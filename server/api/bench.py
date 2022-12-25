# Copyright (C) 2022 SUSE, LLC
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at
# your option) any later version.
from datetime import datetime as dt
from typing import Dict, List, Optional
from uuid import UUID

from fastapi import Request, Depends, HTTPException, status
from fastapi.routing import APIRouter
from pydantic import BaseModel

from common.error import NoSuchConfigError, NoSuchRunError
from controllers.bench.mgr import (
    BenchConfig,
    BenchConfigDesc,
    BenchRunDesc,
    BenchmarkMgr,
)
from api import bench_mgr
from controllers.bench.results import ResultItem
from libstuff.bench.plots import Histogram

router: APIRouter = APIRouter(prefix="/bench", tags=["benchmarking"])


class BenchStartReply(BaseModel):
    date: dt = dt.now()
    uuid: UUID


class BenchGetResultsReply(BaseModel):
    date: dt = dt.now()
    results: Dict[UUID, ResultItem]


class BenchGetResultsHistogramsReply(BaseModel):
    date: dt = dt.now()
    results: Dict[str, Dict[str, Histogram]]


class BenchStatusReply(BaseModel):
    date: dt = dt.now()
    available: bool
    busy: bool
    current: Optional[BenchRunDesc]


class BenchGetConfigReply(BaseModel):
    date: dt = dt.now()
    entries: List[BenchConfigDesc]


class BenchPostConfigReply(BaseModel):
    date: dt = dt.now()
    uuid: UUID


@router.post("/run", response_model=BenchStartReply)
async def run_bench(
    request: Request, uuid: UUID, mgr: BenchmarkMgr = Depends(bench_mgr)
) -> BenchStartReply:

    try:
        config: BenchConfigDesc = await mgr.config_get(uuid=uuid)
    except NoSuchConfigError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    run_uuid = await mgr.run(config)
    return BenchStartReply(uuid=run_uuid)


@router.get("/results", response_model=BenchGetResultsReply)
async def get_results(
    request: Request, mgr: BenchmarkMgr = Depends(bench_mgr)
) -> BenchGetResultsReply:

    return BenchGetResultsReply(results=mgr.results)


@router.get(
    "/results/histograms", response_model=BenchGetResultsHistogramsReply
)
async def get_results_histograms(
    request: Request, uuid: UUID, mgr: BenchmarkMgr = Depends(bench_mgr)
) -> BenchGetResultsHistogramsReply:
    try:
        res = await mgr.get_histograms(uuid)
        return BenchGetResultsHistogramsReply(results=res)
    except NoSuchRunError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)


@router.get("/status", response_model=BenchStatusReply)
async def get_status(
    request: Request, mgr: BenchmarkMgr = Depends(bench_mgr)
) -> BenchStatusReply:

    return BenchStatusReply(
        available=mgr.is_available(),
        busy=mgr.is_busy(),
        current=await mgr.current(),
    )


@router.get("/config", response_model=BenchGetConfigReply)
async def get_config(
    request: Request, mgr: BenchmarkMgr = Depends(bench_mgr)
) -> BenchGetConfigReply:
    return BenchGetConfigReply(entries=await mgr.config_list())


@router.post("/config", response_model=BenchPostConfigReply)
async def post_config(
    request: Request,
    config: BenchConfig,
    mgr: BenchmarkMgr = Depends(bench_mgr),
) -> BenchPostConfigReply:

    uuid: UUID = await mgr.config_create(config)
    return BenchPostConfigReply(uuid=uuid)
