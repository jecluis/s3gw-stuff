# Copyright (C) 2022 SUSE, LLC
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at
# your option) any later version.

import asyncio
from datetime import datetime as dt
from pathlib import Path
from typing import Dict, List, Optional, Tuple, cast
from uuid import UUID, uuid4

from controllers.s3tests.config import (
    S3TestsConfigDesc,
    S3TestsConfigEntry,
)
from fastapi.logger import logger
from libstuff import git
from common.error import ServerError
from libstuff.dbm import DBM
from libstuff.s3tests.runner import S3TestsRunner, S3TestsError, RunnerError
from pydantic import BaseModel


class NoSuchConfigError(ServerError):
    pass


class S3TestRunResult(BaseModel):
    uuid: UUID
    time_start: Optional[dt]
    time_end: Optional[dt]
    results: Dict[str, str]
    is_error: bool
    error_msg: str
    config: S3TestsConfigEntry


class WorkItem:
    _uuid: UUID
    _runner: S3TestsRunner
    _config: S3TestsConfigEntry
    _task: Optional[asyncio.Task[None]]
    _results: List[Tuple[str, str]]
    _is_running: bool
    _is_done: bool
    _is_error: bool
    _error_str: Optional[str]
    _time_start: Optional[dt]
    _time_end: Optional[dt]

    _progress_total: int
    _progress_curr: int

    def __init__(
        self, runner: S3TestsRunner, config: S3TestsConfigEntry
    ) -> None:
        self._uuid = uuid4()
        self._runner = runner
        self._config = config
        self._task = None
        self._results = []
        self._is_running = False
        self._is_done = False
        self._is_error = False
        self._error_str = None
        self._time_start = None
        self._time_end = None
        self._progress_total = 0
        self._progress_curr = 0

    async def run(self) -> UUID:
        if self._is_running or self._is_done:
            return self._uuid

        assert not self._task
        self._task = asyncio.create_task(self._run())
        return self._uuid

    def _progress_cb(self, total: int, progress: int) -> None:
        self._progress_total = total
        self._progress_curr = progress
        logger.debug(f"current progress: {progress}/{total}")

    async def _run(self) -> None:
        self._is_running = True
        try:
            _config = self._config.desc.config
            self._time_start = dt.now()
            self._results = await self._runner.run(
                _config.container, _config.tests, self._progress_cb
            )
        except (S3TestsError, RunnerError) as e:
            logger.error(f"error running s3tests: {e}")
            self._is_error = True
            self._error_str = str(e)

        self._time_end = dt.now()
        self._is_done = True

    async def stop(self) -> None:
        if self._task is not None:
            logger.debug(f"stopping work item task...")
            self._task.cancel()
        self._is_done = True
        self._is_running = False

    @property
    def results(self) -> S3TestRunResult:
        res = {k: v for k, v in self._results}
        return S3TestRunResult(
            uuid=self._uuid,
            time_start=self._time_start,
            time_end=self._time_end,
            results=res,
            is_error=self.is_error(),
            error_msg=self.error,
            config=self._config,
        )

    @property
    def uuid(self) -> UUID:
        return self._uuid

    def is_running(self) -> bool:
        return self._is_running and not self._is_done

    def is_done(self) -> bool:
        return self._is_done

    def is_error(self) -> bool:
        return self._is_error

    @property
    def error(self) -> str:
        return "" if self._error_str is None else self._error_str


class S3TestsMgr:

    _lock: asyncio.Lock
    _task: Optional[asyncio.Task[None]]
    _is_shutting_down: bool

    _db: DBM

    _work_item: Optional[WorkItem]
    _results: Dict[UUID, S3TestRunResult]

    NS_UUID = "s3tests-config"
    NS_NAME = "s3tests-config-by-name"
    NS_TESTS = "s3tests-results"

    def __init__(self, db: DBM) -> None:
        self._lock = asyncio.Lock()
        self._task = None
        self._is_shutting_down = False
        self._db = db
        self._work_item = None
        self._results = {}

    async def start(self) -> None:
        if self._task is not None:
            return

        db_entries = cast(
            Dict[str, S3TestRunResult],
            await self._db.entries(ns=self.NS_TESTS, model=S3TestRunResult),
        )
        for k, v in db_entries.items():
            self._results[UUID(k)] = v

        self._task = asyncio.create_task(self._tick())
        pass

    async def stop(self) -> None:
        self._is_shutting_down = True
        if self._task is not None:
            await self._task

    async def _tick(self) -> None:
        while not self._is_shutting_down:
            logger.debug("tick s3tests runner")
            if self._work_item is not None:
                uuid = self._work_item.uuid
                if self._work_item.is_done():
                    res = self._work_item.results
                    await self._db.put(
                        ns=self.NS_TESTS, key=str(uuid), value=res
                    )
                    self._results[uuid] = res
                    self._work_item = None
                else:
                    logger.debug(f"work item {uuid} running...")

            await asyncio.sleep(1.0)

        if self._work_item is not None:
            logger.debug(f"stopping work item {self._work_item.uuid}...")
            await self._work_item.stop()

        logger.debug("finishing s3tests runner")
        pass

    def is_running(self) -> bool:
        return not self._is_shutting_down and self._task is not None

    async def run(self, cfg: S3TestsConfigEntry) -> UUID:
        async with self._lock:
            if self._work_item is not None:
                return self._work_item.uuid

            isodate = dt.now().isoformat()
            run_name = f"s3tests-{isodate}"
            s3testspath = Path("./s3tests.git").resolve()
            if not s3testspath.exists():
                s3testspath.parent.mkdir(exist_ok=True, parents=True)
                try:
                    git.clone("https://github.com/ceph/s3-tests", s3testspath)
                except git.GitError as e:
                    logger.error(
                        f"error cloning repository to {s3testspath}: {e}"
                    )
                    raise ServerError(
                        f"error cloning repository to {s3testspath}"
                    )

            _config = cfg.desc.config
            runner: S3TestsRunner = S3TestsRunner(
                run_name,
                _config.tests.suite,
                s3testspath,
                logger,
            )
            self._work_item = WorkItem(runner, cfg)
            return await self._work_item.run()
        pass

    async def config_create(self, desc: S3TestsConfigDesc) -> UUID:
        name = desc.name.strip()

        async with self._db.transaction() as tx:
            if tx.exists(self.NS_NAME, name):
                uuid_raw: Optional[str] = tx.get(ns=self.NS_NAME, key=name)
                assert uuid_raw is not None
                return UUID(uuid_raw)

            uuid = uuid4()
            entry = S3TestsConfigEntry(uuid=uuid, desc=desc)
            tx.put(self.NS_UUID, str(uuid), entry)
            tx.put(self.NS_NAME, desc.name, str(uuid))
            return uuid

    async def config_list(self) -> List[S3TestsConfigEntry]:
        entries = await self._db.entries(
            ns=self.NS_UUID, model=S3TestsConfigEntry
        )
        lst: List[S3TestsConfigEntry] = [
            cast(S3TestsConfigEntry, v) for v in entries.values()
        ]
        return lst

    async def config_get(
        self, *, name: Optional[str] = None, uuid: Optional[UUID] = None
    ) -> S3TestsConfigEntry:

        _uuid: Optional[UUID] = uuid
        if name is not None:
            ptr: Optional[str] = await self._db.get(ns=self.NS_NAME, key=name)
            if ptr is None:
                raise NoSuchConfigError()
            _uuid = UUID(ptr)

        if _uuid is None:
            raise NoSuchConfigError()

        cfg: Optional[S3TestsConfigEntry] = await self._db.get_model(
            ns=self.NS_UUID, key=str(_uuid), model=S3TestsConfigEntry
        )
        if cfg is None:
            raise NoSuchConfigError()

        return cfg

    @property
    def results(self) -> Dict[UUID, S3TestRunResult]:
        return self._results
