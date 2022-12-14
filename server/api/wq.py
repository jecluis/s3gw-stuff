# Copyright (C) 2022 SUSE, LLC
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at
# your option) any later version.

from api import workqueue
from controllers.wq.status import WorkQueueState, WorkQueueStatus
from controllers.wq.wq import WorkQueue
from fastapi import Depends, Request
from fastapi.routing import APIRouter
from pydantic import BaseModel

router: APIRouter = APIRouter(prefix="/workqueue", tags=["workqueue"])


class WorkQueueGetReply(BaseModel):
    status: WorkQueueState


class WorkQueueGetStatusReply(BaseModel):
    status: WorkQueueStatus


@router.get("/", response_model=WorkQueueGetReply)
async def get_workqueue(
    request: Request, wq: WorkQueue = Depends(workqueue)
) -> WorkQueueGetReply:
    return WorkQueueGetReply(status=await wq.state())


@router.get("/status", response_model=WorkQueueGetStatusReply)
async def get_workqueue_status(
    request: Request, wq: WorkQueue = Depends(workqueue)
) -> WorkQueueGetStatusReply:
    return WorkQueueGetStatusReply(status=await wq.status())
