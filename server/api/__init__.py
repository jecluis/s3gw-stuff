# Copyright (C) 2022 SUSE, LLC
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at
# your option) any later version.

from controllers.context import ServerContext
from controllers.s3tests.mgr import S3TestsMgr
from fastapi import Request


class APIServerContext:
    def __init__(self) -> None:
        pass

    def __call__(self, request: Request) -> ServerContext:
        ctx: ServerContext = request.app.state.ctx
        return ctx


class APIS3TestsMgr:
    def __init__(self) -> None:
        pass

    def __call__(self, request: Request) -> S3TestsMgr:
        ctx: ServerContext = request.app.state.ctx
        return ctx.s3tests


server_context = APIServerContext()
s3tests_mgr = APIS3TestsMgr()
