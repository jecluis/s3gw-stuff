# Copyright (C) 2022 SUSE, LLC
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at
# your option) any later version.

import asyncio
from datetime import datetime as dt
import logging
import random
import shutil
from typing import Dict, List, Optional, cast
from uuid import UUID, uuid4

from pydantic import BaseModel
from libstuff.bench.plots import Histogram

from libstuff.bench.runner import (
    BenchmarkPorts,
    BenchmarkRunner,
    BenchmarkTarget,
)
from libstuff.bench.warp import WarpBenchmarkState
from libstuff.dbm import DBM
from common.error import NoSuchConfigError
from controllers.bench.types import (
    BenchConfig,
    BenchConfigDesc,
    BenchDBNS,
    BenchProgress,
    BenchResult,
    BenchTarget,
    BenchTargetError,
    TargetProgress,
)
from controllers.bench.results import ResultItem, Results


def _gen_random_host_port() -> int:
    FIRST_PORT = 54780
    LAST_PORT = 54880
    return random.choice(list(range(FIRST_PORT, LAST_PORT)))


class BenchRunDesc(BaseModel):
    config: BenchConfig
    progress: BenchProgress


class WorkItem:
    _uuid: UUID
    _runner: BenchmarkRunner
    _config: BenchConfig
    _task: Optional[asyncio.Task[None]]
    _is_running: bool
    _is_done: bool
    _time_start: Optional[dt]
    _time_end: Optional[dt]

    _progress_by_target: Dict[str, TargetProgress]
    _results: Dict[str, str]

    logger: logging.Logger

    def __init__(
        self,
        runner: BenchmarkRunner,
        config: BenchConfig,
        logger: logging.Logger,
    ) -> None:
        self._uuid = uuid4()
        self._runner = runner
        self._config = config
        self._task = None
        self._is_running = False
        self._is_done = False
        self._time_start = None
        self._time_end = None
        self._progress_by_target = {}
        self._results = {}
        self.logger = logger

    async def run(self) -> UUID:
        if self._is_running or self._is_done:
            return self._uuid

        for target in self._config.targets.keys():
            self._progress_by_target[target] = TargetProgress(
                name=target,
                state=WarpBenchmarkState.NONE,
                value=0.0,
                has_progress=False,
                is_running=False,
                is_done=False,
                is_error=False,
                error_str=None,
                time_start=None,
                time_end=None,
                duration=0,
            )

        assert not self._task
        self._task = asyncio.create_task(self._run())
        return self._uuid

    async def _run(self) -> None:
        self._is_running = True
        self._time_start = dt.now()

        for target, conf in self._config.targets.items():
            await self._run_target(target, conf)

        self._time_end = dt.now()
        self._is_done = True

    async def _run_target(self, target: str, config: BenchTarget) -> None:

        host_port: int = _gen_random_host_port()
        target_conf = BenchmarkTarget(
            image=config.image,
            args=config.args,
            volumes=None,
            ports=[BenchmarkPorts(source=host_port, target=config.port)],
            access_key=config.access_key,
            secret_key=config.secret_key,
            host=f"127.0.0.1:{host_port}",
        )

        assert target in self._progress_by_target
        progress: TargetProgress = self._progress_by_target[target]

        try:
            progress.time_start = dt.now()
            progress.is_running = True
            res: str = await self._runner.run(
                target, target_conf, progress.progress_cb
            )
            progress.time_end = dt.now()
            self._results[target] = res
        except Exception as e:
            self.logger.error(f"error running benchmark target {target}: {e}")
            progress.is_error = True
            progress.error_str = str(e)

        progress.is_done = True
        progress.is_running = False

    async def stop(self) -> None:
        if self._task is not None:
            self.logger.debug("stopping work item task...")
            self._task.cancel()

        for target in self._progress_by_target.values():
            target.is_done = True
            target.is_running = False
            if target.time_start is not None and target.time_end is None:
                target.time_end = dt.now()

        self._is_done = True
        self._is_running = False

    @property
    def progress(self) -> BenchProgress:
        lst: List[TargetProgress] = []
        for target in self._progress_by_target.values():
            tgt = target.copy()
            if tgt.time_start is not None:
                end = tgt.time_end if tgt.time_end is not None else dt.now()
                tgt.duration = (end - tgt.time_start).seconds
            lst.append(tgt)

        duration = 0
        if self._time_start is not None:
            end = self._time_end if self._time_end is not None else dt.now()
            duration = (end - self._time_start).seconds

        return BenchProgress(
            is_running=self._is_running,
            is_done=self._is_done,
            time_start=self._time_start,
            time_end=self._time_end,
            duration=duration,
            targets=lst,
        )

    @property
    def results(self) -> BenchResult:
        errors: List[BenchTargetError] = []
        for target, progress in self._progress_by_target.items():
            if not progress.is_error:
                continue
            assert progress.error_str is not None
            errors.append(
                BenchTargetError(target=target, error_str=progress.error_str)
            )

        return BenchResult(
            uuid=self._uuid,
            progress=self.progress,
            is_error=(len(errors) > 0),
            errors=errors,
            config=self._config,
            results=self._results,
        )

    @property
    def uuid(self) -> UUID:
        return self._uuid

    @property
    def config(self) -> BenchConfig:
        return self._config

    def is_running(self) -> bool:
        return self._is_running

    def is_done(self) -> bool:
        return self._is_done


class BenchmarkMgr:

    _lock: asyncio.Lock
    _configs_lock: asyncio.Lock
    _task: Optional[asyncio.Task[None]]
    _is_shutting_down: bool
    _is_running: bool
    _has_error: bool
    _error_str: Optional[str]

    _db: DBM

    _work_item: Optional[WorkItem]
    _results: Results
    _configs: Dict[UUID, BenchConfig]

    logger: logging.Logger

    NS_CONFIG_BY_UUID = BenchDBNS.NS_CONFIG_BY_UUID
    NS_CONFIG_BY_NAME = BenchDBNS.NS_CONFIG_BY_NAME
    NS_RESULTS = BenchDBNS.NS_RESULTS
    NS_CONFIG_RESULTS = BenchDBNS.NS_CONFIG_RESULTS

    def __init__(self, db: DBM, logger: logging.Logger) -> None:
        self._lock = asyncio.Lock()
        self._configs_lock = asyncio.Lock()
        self._task = None
        self._is_shutting_down = False
        self._is_running = False
        self._has_error = False
        self._error_str = None
        self._db = db
        self._work_item = None
        self._results = Results(db, logger)
        self._configs = {}
        self.logger = logger

    async def start(self) -> None:
        if self._is_running:
            return

        if not self._can_run():
            self.logger.error(
                f"unable to start benchmark mgr: {self._error_str}"
            )
            return

        await self._load_results()
        await self._load_configs()
        await self._results.start()
        self._task = asyncio.create_task(self._tick())

    async def stop(self) -> None:
        if self._task is None:
            return
        self._is_shutting_down = True
        await self._results.stop()
        await self._task

    def _can_run(self) -> bool:
        if shutil.which("warp") is None:
            self._error_str = "unable to find warp command."
            self._has_error = True
            return False
        return True

    async def _load_results(self) -> None:
        entries = cast(
            Dict[str, BenchResult],
            await self._db.entries(ns=self.NS_RESULTS, model=BenchResult),
        )
        for res in entries.values():
            await self._results.add(res)

    async def _load_configs(self) -> None:
        entries = cast(
            Dict[str, BenchConfig],
            await self._db.entries(
                ns=self.NS_CONFIG_BY_UUID, model=BenchConfig
            ),
        )
        for uuid, cfg in entries.items():
            await self._add_config(UUID(uuid), cfg)

    async def _tick(self) -> None:
        self._is_running = True
        while not self._is_shutting_down:
            if self._work_item is not None:
                if self._work_item.is_done():
                    await self._handle_work_item_results()
                else:
                    self.logger.debug(
                        f"work item {self._work_item.uuid} running..."
                    )
            self.logger.debug("tick bench mgr")
            await asyncio.sleep(1.0)

        if self._work_item is not None:
            self.logger.debug(f"stoping work item {self._work_item.uuid}...")
            await self._work_item.stop()

        self.logger.debug("finishing benchmark mgr tick")
        self._is_running = False

    async def _handle_work_item_results(self) -> None:
        assert self._work_item is not None
        assert self._work_item.is_done()

        uuid = self._work_item.uuid

        # handle work item results
        res = self._work_item.results
        await self._db.put(ns=self.NS_RESULTS, key=str(uuid), value=res)
        await self._results.add(res)

        self._work_item = None

    def is_running(self) -> bool:
        return self._is_running and not self._is_shutting_down

    def is_busy(self) -> bool:
        return self.is_running() and self._work_item is not None

    async def current(self) -> Optional[BenchRunDesc]:
        async with self._lock:
            wi = self._work_item
            if wi is None:
                return None

            return BenchRunDesc(
                config=wi.config,
                progress=wi.progress,
            )

    async def run(self, cfg: BenchConfig) -> UUID:
        async with self._lock:
            if self._work_item is not None:
                return self._work_item.uuid

            date = dt.now().strftime("%Y%m%d-%H%M%S")
            run_name = f"benchmark-{date}"

            runner = BenchmarkRunner(run_name, cfg.params, self.logger)
            self._work_item = WorkItem(runner, cfg, self.logger)
            return await self._work_item.run()

    async def config_create(self, cfg: BenchConfig) -> UUID:
        async with self._db.transaction() as tx:
            if tx.exists(self.NS_CONFIG_BY_NAME, cfg.name):
                uuid_raw: Optional[str] = tx.get(
                    ns=self.NS_CONFIG_BY_NAME, key=cfg.name
                )
                assert uuid_raw is not None
                return UUID(uuid_raw)

            uuid = uuid4()
            tx.put(self.NS_CONFIG_BY_UUID, key=str(uuid), value=cfg)
            tx.put(self.NS_CONFIG_BY_NAME, key=cfg.name, value=str(uuid))

        await self._add_config(uuid, cfg)
        return uuid

    async def _add_config(self, uuid: UUID, cfg: BenchConfig) -> None:
        async with self._configs_lock:
            self._configs[uuid] = cfg

    async def config_list(self) -> List[BenchConfigDesc]:
        lst: List[BenchConfigDesc] = []
        async with self._configs_lock:
            for uuid, cfg in self._configs.items():
                lst.append(BenchConfigDesc(uuid=uuid, config=cfg))
        return lst

    async def config_get(
        self, *, name: Optional[str] = None, uuid: Optional[UUID] = None
    ) -> BenchConfig:

        _uuid: Optional[UUID] = uuid
        if name is not None:
            ptr: Optional[str] = await self._db.get(
                ns=self.NS_CONFIG_BY_NAME, key=name
            )
            if ptr is None:
                raise NoSuchConfigError()
            _uuid = UUID(ptr)

        if _uuid is None:
            raise NoSuchConfigError()

        async with self._configs_lock:
            if _uuid not in self._configs:
                raise NoSuchConfigError()
            return self._configs[_uuid]

    async def get_histograms(
        self, uuid: UUID
    ) -> Dict[str, Dict[str, Histogram]]:
        return await self._results.get_histograms(uuid)

    @property
    def results(self) -> Dict[UUID, ResultItem]:
        return self._results.results
