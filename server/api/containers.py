# Copyright (C) 2022 SUSE, LLC
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at
# your option) any later version.

from datetime import datetime as dt
from typing import List

from fastapi import Request
from fastapi.routing import APIRouter
from libstuff import podman
from pydantic import BaseModel

router: APIRouter = APIRouter(prefix="/containers", tags=["containers"])


class ContainerPSReply(BaseModel):
    date: dt
    result: List[podman.PodmanContainer]


@router.get("/ps", response_model=ContainerPSReply)
async def get_ps(request: Request) -> ContainerPSReply:
    return ContainerPSReply(date=dt.now(), result=await podman.ps())
