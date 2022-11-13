# Copyright (C) 2022 SUSE, LLC
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at
# your option) any later version.

from controllers.config import ServerConfig
from controllers.s3tests.mgr import S3TestsMgr


class ServerContext:

    _s3tests: S3TestsMgr
    _config: ServerConfig

    def __init__(self, config: ServerConfig) -> None:
        self._config = config
        self._s3tests = S3TestsMgr(self._config.s3tests)
        pass

    async def start(self) -> None:
        await self._s3tests.start()
        pass

    async def stop(self) -> None:
        await self._s3tests.stop()
        pass

    @property
    def s3tests(self) -> S3TestsMgr:
        return self._s3tests
