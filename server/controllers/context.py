# Copyright (C) 2022 SUSE, LLC
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at
# your option) any later version.

from pathlib import Path

from fastapi.logger import logger
from libstuff.dbm import DBM
from controllers.config import ServerConfig
from controllers.s3tests.mgr import S3TestsMgr
from controllers.bench.mgr import BenchmarkMgr
from controllers.wq.wq import WorkQueue


class ServerContext:

    _s3tests: S3TestsMgr
    _bench: BenchmarkMgr
    _config: ServerConfig
    _wq: WorkQueue
    _db: DBM

    def __init__(self, config: ServerConfig) -> None:
        self._config = config
        _dbpath = Path("./server.db").resolve()
        self._db = DBM(_dbpath)
        self._wq = WorkQueue(logger)

        self._s3tests = S3TestsMgr(self._db, self._wq)
        self._bench = BenchmarkMgr(self._db, self._wq, logger)

    async def start(self) -> None:
        await self._s3tests.start()
        await self._bench.start()
        await self._wq.start()

    async def stop(self) -> None:
        await self._wq.stop()
        await self._s3tests.stop()
        await self._bench.stop()

    @property
    def s3tests(self) -> S3TestsMgr:
        return self._s3tests

    @property
    def bench(self) -> BenchmarkMgr:
        return self._bench

    @property
    def workqueue(self) -> WorkQueue:
        return self._wq
