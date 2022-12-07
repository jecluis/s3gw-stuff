# Copyright (C) 2022 SUSE, LLC
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at
# your option) any later version.
from datetime import datetime as dt
from typing import Dict, Optional
from uuid import UUID

from fastapi import Request, Depends
from fastapi.routing import APIRouter
from pydantic import BaseModel

from libstuff.bench.runner import (
    BenchmarkParams,
)
from controllers.bench.mgr import (
    BenchConfig,
    BenchResult,
    BenchRunDesc,
    BenchTarget,
    BenchmarkMgr,
)
from api import bench_mgr

router: APIRouter = APIRouter(prefix="/bench", tags=["benchmarking"])


class BenchStartReply(BaseModel):
    date: dt = dt.now()
    uuid: UUID


class BenchGetResultsReply(BaseModel):
    date: dt = dt.now()
    results: Dict[UUID, BenchResult]


class BenchStatusReply(BaseModel):
    date: dt = dt.now()
    running: bool
    busy: bool
    current: Optional[BenchRunDesc]


@router.post("/run", response_model=BenchStartReply)
async def run_bench(
    request: Request, mgr: BenchmarkMgr = Depends(bench_mgr)
) -> BenchStartReply:

    params = BenchmarkParams(
        num_objects=100, object_size="100KB", duration="1m"
    )
    target = BenchTarget(
        image="ghcr.io/aquarist-labs/s3gw:latest",
        access_key="test",
        secret_key="test",
        port=7480,
        args=None,
    )
    config = BenchConfig(
        name="test config",
        params=params,
        targets={"s3gw": target},
    )

    uuid = await mgr.run(config)
    return BenchStartReply(uuid=uuid)


@router.get("/results", response_model=BenchGetResultsReply)
async def get_results(
    request: Request, mgr: BenchmarkMgr = Depends(bench_mgr)
) -> BenchGetResultsReply:

    return BenchGetResultsReply(results=mgr.results)


@router.get("/status", response_model=BenchStatusReply)
async def get_status(
    request: Request, mgr: BenchmarkMgr = Depends(bench_mgr)
) -> BenchStatusReply:

    return BenchStatusReply(
        running=mgr.is_running(),
        busy=mgr.is_busy(),
        current=await mgr.current(),
    )
