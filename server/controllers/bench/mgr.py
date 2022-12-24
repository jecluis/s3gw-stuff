# Copyright (C) 2022 SUSE, LLC
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at
# your option) any later version.

import asyncio
import logging
import random
import shutil
from datetime import datetime as dt
from typing import Dict, List, Optional, cast
from uuid import UUID, uuid4

from common.error import NoSuchConfigError
from controllers.bench.config import BenchConfigDesc, BenchTarget
from controllers.bench.progress import BenchTargetsProgress, TargetProgress
from controllers.bench.results import ResultItem, Results
from controllers.bench.types import (
    BenchConfig,
    BenchDBNS,
    BenchProgress,
    BenchResult,
    BenchTargetError,
)
from controllers.wq.types import WQItemConfigType, WQItemProgressType
from controllers.wq.wq import WorkQueue, WQItem, WQItemCB, WQItemKind
from libstuff.bench.plots import Histogram
from libstuff.bench.runner import (
    BenchmarkPorts,
    BenchmarkRunner,
    BenchmarkTarget,
)
from libstuff.bench.warp import WarpBenchmarkState
from libstuff.dbm import DBM
from pydantic import BaseModel


def _gen_random_host_port() -> int:
    FIRST_PORT = 54780
    LAST_PORT = 54880
    return random.choice(list(range(FIRST_PORT, LAST_PORT)))


class BenchRunDesc(BaseModel):
    config: BenchConfig
    progress: BenchProgress


class WorkItem(WQItem):
    _runner: BenchmarkRunner
    _config: BenchConfig

    _progress_by_target: Dict[str, TargetProgress]
    _results: Dict[str, str]

    def __init__(
        self,
        runner: BenchmarkRunner,
        config: BenchConfig,
        logger: logging.Logger,
    ) -> None:
        super().__init__(logger)
        self._runner = runner
        self._config = config
        self._progress_by_target = {}
        self._results = {}

    async def _run(self) -> None:

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

        for target, conf in self._config.targets.items():
            await self._run_target(target, conf)

        await asyncio.sleep(10)

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

    async def _stop(self) -> None:
        for target in self._progress_by_target.values():
            target.is_done = True
            target.is_running = False
            if target.time_start is not None and target.time_end is None:
                target.time_end = dt.now()

    @property
    def _progress(self) -> WQItemProgressType:
        lst: List[TargetProgress] = []
        for target in self._progress_by_target.values():
            tgt = target.copy()
            if tgt.time_start is not None:
                end = tgt.time_end if tgt.time_end is not None else dt.now()
                tgt.duration = (end - tgt.time_start).seconds
            lst.append(tgt)

        return cast(
            WQItemProgressType,
            BenchTargetsProgress(
                targets=lst,
            ),
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
    def config(self) -> WQItemConfigType:
        return cast(WQItemConfigType, self._config)


class BenchmarkMgr:

    _lock: asyncio.Lock
    _configs_lock: asyncio.Lock
    _task: Optional[asyncio.Task[None]]
    _is_shutting_down: bool
    _is_available: bool
    _is_busy: bool
    _has_error: bool
    _error_str: Optional[str]

    _db: DBM
    _wq: WorkQueue

    # _work_item: Optional[WorkItem]
    _current: Optional[WorkItem]
    _results: Results
    _configs: Dict[UUID, BenchConfig]

    logger: logging.Logger

    NS_CONFIG_BY_UUID = BenchDBNS.NS_CONFIG_BY_UUID
    NS_CONFIG_BY_NAME = BenchDBNS.NS_CONFIG_BY_NAME
    NS_RESULTS = BenchDBNS.NS_RESULTS
    NS_CONFIG_RESULTS = BenchDBNS.NS_CONFIG_RESULTS

    def __init__(self, db: DBM, wq: WorkQueue, logger: logging.Logger) -> None:
        self._lock = asyncio.Lock()
        self._configs_lock = asyncio.Lock()
        self._task = None
        self._is_shutting_down = False
        self._is_available = False
        self._is_busy = False
        self._has_error = False
        self._error_str = None
        self._db = db
        self._wq = wq
        # self._work_item = None
        self._current = None
        self._results = Results(db, logger)
        self._configs = {}
        self.logger = logger

    async def start(self) -> None:
        if self._is_available:
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

        tmp = await self._db.entries(ns=self.NS_RESULTS)
        for res in tmp.keys():
            self.logger.debug(f"remove key {res}")
            await self._db.rm(ns=self.NS_RESULTS, key=res)

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
        self._is_available = True
        while not self._is_shutting_down:
            # if self._work_item is not None:
            #     if self._work_item.is_done():
            #         await self._handle_work_item_results()
            #     else:
            #         self.logger.debug(
            #             f"work item {self._work_item.uuid} running..."
            #         )
            self.logger.debug("tick bench mgr")
            await asyncio.sleep(1.0)

        # if self._work_item is not None:
        #     self.logger.debug(f"stoping work item {self._work_item.uuid}...")
        #     await self._work_item.stop()

        self.logger.debug("finishing benchmark mgr tick")
        self._is_available = False

    async def _handle_work_item_results(self, item: WorkItem) -> None:
        assert item.is_done()

        uuid = item.uuid

        # handle work item results
        res = item.results
        await self._db.put(ns=self.NS_RESULTS, key=str(uuid), value=res)
        await self._results.add(res)
        # self._work_item = None

    def is_available(self) -> bool:
        return self._is_available and not self._is_shutting_down

    def is_busy(self) -> bool:
        return self.is_available() and self._is_busy

    async def current(self) -> Optional[BenchRunDesc]:
        async with self._lock:
            if self._current is None:
                return None

            return BenchRunDesc(
                config=cast(BenchConfig, self._current.config),
                progress=self._current.progress,
            )

    async def _handle_finished_item(self, item: WQItem) -> None:
        _item: WorkItem = cast(WorkItem, item)
        self.logger.debug(f"finished work item uuid {_item.uuid}")
        async with self._lock:
            assert self._is_busy
            assert self._current is not None
            assert self._current.uuid == _item.uuid
            await self._handle_work_item_results(_item)
            self._is_busy = False
            self._current = None

    async def _handle_started_item(self, item: WQItem) -> None:
        _item: WorkItem = cast(WorkItem, item)
        self.logger.debug(f"starting work item uuid {_item.uuid}")
        async with self._lock:
            assert not self._is_busy
            assert self._current is None
            self._current = _item
            self._is_busy = True

    async def run(self, cfg: BenchConfig) -> UUID:
        date = dt.now().strftime("%Y%m%d-%H%M%S")
        run_name = f"benchmark-{date}"

        runner = BenchmarkRunner(run_name, cfg.params, self.logger)
        item = WorkItem(runner, cfg, self.logger)
        cb: WQItemCB = WQItemCB(
            start=self._handle_started_item, finish=self._handle_finished_item
        )
        await self._wq.put(item, WQItemKind.BENCH, cb)
        return item.uuid

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
