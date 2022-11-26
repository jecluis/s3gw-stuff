# Copyright (C) 2022 SUSE, LLC
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at
# your option) any later version.

import asyncio
from datetime import datetime as dt
from pathlib import Path
import random
import string
from typing import Dict, List, Optional, cast
from uuid import UUID, uuid4

from controllers.s3tests.config import (
    S3TestsConfigDesc,
    S3TestsConfigEntry,
)
from fastapi.logger import logger
from libstuff import git
from common.error import ServerError
from libstuff.dbm import DBM
from libstuff.s3tests.runner import (
    CollectedTests,
    ContainerRunConfig,
    ErrorTestResult,
    S3TestsRunner,
    S3TestsError,
    RunnerError,
    TestRunResult,
)
from pydantic import BaseModel


class NoSuchConfigError(ServerError):
    pass


class NoSuchRunError(ServerError):
    pass


class S3TestRunProgress(BaseModel):
    tests_total: int
    tests_run: int

    @property
    def progress(self) -> float:
        if self.tests_total == 0:
            return 100
        return (self.tests_run * 100) / self.tests_total


class S3TestRunDesc(BaseModel):
    uuid: UUID
    time_start: Optional[dt]
    config: S3TestsConfigEntry
    progress: Optional[S3TestRunProgress]


class S3TestRunResult(S3TestRunDesc):
    time_end: Optional[dt]
    results: Dict[str, str]
    is_error: bool
    error_msg: str


class S3TestsConfigItem(BaseModel):
    config: S3TestsConfigEntry
    tests: CollectedTests


def _gen_random_container_name() -> str:
    rnd = "".join(random.choices(string.ascii_lowercase, k=4))
    ts = dt.now().isoformat(timespec="minutes")
    return f"s3tests-{ts}-{rnd}"


def _gen_random_container_port() -> int:
    FIRST_PORT = 44780
    LAST_PORT = 44880
    ports = list(range(FIRST_PORT, LAST_PORT))
    return random.choice(ports)


class WorkItem:
    _uuid: UUID
    _runner: S3TestsRunner
    _config: S3TestsConfigEntry
    _task: Optional[asyncio.Task[None]]
    _results: TestRunResult
    _is_running: bool
    _is_done: bool
    _is_error: bool
    _error_str: Optional[str]
    _time_start: Optional[dt]
    _time_end: Optional[dt]

    _progress_total: int
    _progress_curr: int
    _has_progress: bool

    def __init__(
        self, runner: S3TestsRunner, config: S3TestsConfigEntry
    ) -> None:
        self._uuid = uuid4()
        self._runner = runner
        self._config = config
        self._task = None
        self._results = TestRunResult(results=[], errors={})
        self._is_running = False
        self._is_done = False
        self._is_error = False
        self._error_str = None
        self._time_start = None
        self._time_end = None
        self._progress_total = 0
        self._progress_curr = 0
        self._has_progress = False

    async def run(self) -> UUID:
        if self._is_running or self._is_done:
            return self._uuid

        assert not self._task
        self._task = asyncio.create_task(self._run())
        return self._uuid

    def _progress_cb(self, total: int, progress: int) -> None:
        self._has_progress = True
        self._progress_total = total
        self._progress_curr = progress
        logger.debug(f"current progress: {progress}/{total}")

    async def _run(self) -> None:
        self._is_running = True
        try:
            _config = self._config.desc.config
            _cconf = ContainerRunConfig(
                name=_gen_random_container_name(),
                host_port=_gen_random_container_port(),
                config=_config.container,
            )

            self._time_start = dt.now()
            self._results = await self._runner.run(
                _cconf, _config.tests, self._progress_cb
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
    def progress(self) -> Optional[S3TestRunProgress]:
        if not self._has_progress:
            return None
        return S3TestRunProgress(
            tests_total=self._progress_total, tests_run=self._progress_curr
        )

    @property
    def results(self) -> S3TestRunResult:
        res = {k: v for k, v in self._results.results}
        return S3TestRunResult(
            uuid=self._uuid,
            time_start=self._time_start,
            time_end=self._time_end,
            results=res,
            is_error=self.is_error(),
            error_msg=self.error,
            config=self._config,
            progress=self.progress,
        )

    @property
    def errors(self) -> Dict[str, ErrorTestResult]:
        return self._results.errors

    @property
    def uuid(self) -> UUID:
        return self._uuid

    @property
    def desc(self) -> S3TestRunDesc:
        return S3TestRunDesc(
            uuid=self._uuid,
            time_start=self._time_start,
            config=self._config,
            progress=self.progress,
        )

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
    _configs_lock: asyncio.Lock
    _task: Optional[asyncio.Task[None]]
    _is_shutting_down: bool

    _db: DBM
    _s3tests_path: Path

    _work_item: Optional[WorkItem]
    _results: Dict[UUID, S3TestRunResult]
    _configs: Dict[UUID, S3TestsConfigItem]

    NS_UUID = "s3tests-config"
    NS_NAME = "s3tests-config-by-name"
    NS_TESTS = "s3tests-results"
    NS_TESTS_ERRORS = "s3tests-results-errors"

    def __init__(self, db: DBM) -> None:
        self._lock = asyncio.Lock()
        self._configs_lock = asyncio.Lock()
        self._task = None
        self._is_shutting_down = False
        self._db = db
        self._s3tests_path = Path("./s3tests.git").resolve()
        self._work_item = None
        self._results = {}
        self._configs = {}

    async def start(self) -> None:
        if self._task is not None:
            return

        await self._init_s3tests_repo()
        await self._load_results()
        await self._load_configs()

        self._task = asyncio.create_task(self._tick())
        pass

    async def stop(self) -> None:
        self._is_shutting_down = True
        if self._task is not None:
            await self._task

    async def _init_s3tests_repo(self) -> None:
        if self._s3tests_path.exists():
            return

        self._s3tests_path.parent.mkdir(exist_ok=True, parents=True)
        try:
            git.clone("https://github.com/ceph/s3-tests", self._s3tests_path)
        except git.GitError as e:
            logger.error(
                f"error cloning repository to {self._s3tests_path}: {e}"
            )
            raise ServerError(
                f"error cloning repository to {self._s3tests_path}"
            )

    async def _load_results(self) -> None:
        db_entries = cast(
            Dict[str, S3TestRunResult],
            await self._db.entries(ns=self.NS_TESTS, model=S3TestRunResult),
        )
        for k, v in db_entries.items():
            self._results[UUID(k)] = v

    async def _load_configs(self) -> None:
        db_entries = await self._db.entries(
            ns=self.NS_UUID, model=S3TestsConfigEntry
        )
        lst: List[S3TestsConfigEntry] = [
            cast(S3TestsConfigEntry, v) for v in db_entries.values()
        ]
        for entry in lst:
            await self._add_config(entry)

    async def _add_config(self, entry: S3TestsConfigEntry) -> None:
        async with self._configs_lock:
            collected = await self._collect_config_tests(entry)
            self._configs[entry.uuid] = S3TestsConfigItem(
                config=entry, tests=collected
            )
            ntotal = len(collected.all)
            nunits = len(collected.filtered)
            logger.info(f"config {entry.uuid} with {nunits}/{ntotal} units")

    async def _collect_config_tests(
        self, config: S3TestsConfigEntry
    ) -> CollectedTests:

        cfg = config.desc.config.tests
        runner = S3TestsRunner(
            "collect",
            self._s3tests_path,
            logger,
        )
        return await runner.collect(cfg)

    async def _handle_work_item_results(self) -> None:
        assert self._work_item is not None
        assert self._work_item.is_done()

        uuid = self._work_item.uuid

        # handle work item results
        res = self._work_item.results
        await self._db.put(ns=self.NS_TESTS, key=str(uuid), value=res)
        self._results[uuid] = res

        # handle work item errors
        #  stores them at 's3tests-results-errors/uuid/testname'
        errors = self._work_item.errors
        for name, entry in errors.items():
            key = str(uuid) + "/" + name
            await self._db.put(ns=self.NS_TESTS_ERRORS, key=key, value=entry)

        self._work_item = None
        pass

    async def _tick(self) -> None:
        while not self._is_shutting_down:
            logger.debug("tick s3tests runner")
            if self._work_item is not None:
                if self._work_item.is_done():
                    await self._handle_work_item_results()
                else:
                    logger.debug(f"work item {self._work_item.uuid} running...")

            await asyncio.sleep(1.0)

        if self._work_item is not None:
            logger.debug(f"stopping work item {self._work_item.uuid}...")
            await self._work_item.stop()

        logger.debug("finishing s3tests runner")
        pass

    def is_running(self) -> bool:
        return not self._is_shutting_down and self._task is not None

    def is_busy(self) -> bool:
        return self.is_running() and self._work_item is not None

    async def run(self, cfg: S3TestsConfigEntry) -> UUID:
        async with self._lock:
            if self._work_item is not None:
                return self._work_item.uuid

            isodate = dt.now().isoformat()
            run_name = f"s3tests-{isodate}"

            _config = cfg.desc.config
            runner: S3TestsRunner = S3TestsRunner(
                run_name,
                self._s3tests_path,
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

        await self._add_config(entry)
        return uuid

    async def config_list(self) -> List[S3TestsConfigItem]:

        async with self._configs_lock:
            return list(self._configs.values())

        entries = await self._db.entries(
            ns=self.NS_UUID, model=S3TestsConfigEntry
        )
        lst: List[S3TestsConfigEntry] = [
            cast(S3TestsConfigEntry, v) for v in entries.values()
        ]
        return lst

    async def config_get(
        self, *, name: Optional[str] = None, uuid: Optional[UUID] = None
    ) -> S3TestsConfigItem:

        _uuid: Optional[UUID] = uuid
        if name is not None:
            ptr: Optional[str] = await self._db.get(ns=self.NS_NAME, key=name)
            if ptr is None:
                raise NoSuchConfigError()
            _uuid = UUID(ptr)

        if _uuid is None:
            raise NoSuchConfigError()

        async with self._configs_lock:
            if _uuid not in self._configs:
                raise NoSuchConfigError()

            return self._configs[_uuid]

        cfg: Optional[S3TestsConfigEntry] = await self._db.get_model(
            ns=self.NS_UUID, key=str(_uuid), model=S3TestsConfigEntry
        )
        if cfg is None:
            raise NoSuchConfigError()

        return cfg

    def get_run(self, uuid: UUID) -> S3TestRunResult:
        if uuid in self._results:
            return self._results[uuid]

        elif self.is_busy():
            assert self._work_item is not None
            res = self._work_item.results
            if res.uuid == uuid:
                return res

        raise NoSuchRunError()

    async def get_errors(self, uuid: UUID) -> Dict[str, ErrorTestResult]:
        prefix = str(uuid) + "/"
        res: Dict[str, ErrorTestResult] = cast(
            Dict[str, ErrorTestResult],
            await self._db.entries(
                ns=self.NS_TESTS_ERRORS, prefix=prefix, model=ErrorTestResult
            ),
        )
        entries: Dict[str, ErrorTestResult] = {}
        for k, v in res.items():
            assert k.startswith(prefix)
            name = k[len(prefix) :]
            entries[name] = v

        return entries

    async def get_error_for(self, uuid: UUID, name: str) -> ErrorTestResult:
        key = str(uuid) + "/" + name
        res: Optional[ErrorTestResult] = await self._db.get_model(
            ns=self.NS_TESTS_ERRORS, key=key, model=ErrorTestResult
        )
        if not res:
            raise NoSuchRunError()
        return res

    @property
    def results(self) -> Dict[UUID, S3TestRunResult]:
        return self._results

    @property
    def current_run(self) -> Optional[S3TestRunDesc]:
        if not self.is_busy():
            return None
        assert self._work_item is not None
        return self._work_item.desc
