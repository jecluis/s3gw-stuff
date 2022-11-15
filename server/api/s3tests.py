# Copyright (C) 2022 SUSE, LLC
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at
# your option) any later version.

from datetime import datetime as dt
from uuid import UUID
from typing import Dict, List, Optional

from controllers.s3tests.config import S3TestsConfigDesc, S3TestsConfigEntry
from controllers.s3tests.mgr import (
    S3TestsMgr,
    S3TestRunResult,
    NoSuchConfigError,
)
from fastapi import Depends, Request, HTTPException, status
from fastapi.logger import logger
from fastapi.routing import APIRouter
from pydantic import BaseModel

from . import s3tests_mgr

router: APIRouter = APIRouter(prefix="/s3tests", tags=["s3tests"])


class S3TestsBaseReply(BaseModel):
    date: dt = dt.now()


class S3TestsResultsReply(S3TestsBaseReply):
    results: Dict[UUID, S3TestRunResult]


class S3TestsRunReply(S3TestsBaseReply):
    uuid: UUID


class S3TestsInfoReply(S3TestsBaseReply):
    pass


class S3TestsStatusReply(S3TestsBaseReply):
    running: bool


class S3TestsConfigPostReply(S3TestsBaseReply):
    uuid: UUID


class S3TestsConfigGetReply(S3TestsBaseReply):
    config: List[S3TestsConfigEntry]


@router.get("/results", response_model=S3TestsResultsReply)
async def get_results(
    request: Request, mgr: S3TestsMgr = Depends(s3tests_mgr)
) -> S3TestsResultsReply:
    return S3TestsResultsReply(date=dt.now(), results=mgr.results)


@router.post("/run", response_model=S3TestsRunReply)
async def run_s3tests(
    request: Request,
    mgr: S3TestsMgr = Depends(s3tests_mgr),
    name: Optional[str] = None,
    uuid: Optional[UUID] = None,
) -> S3TestsRunReply:

    cfg: Optional[S3TestsConfigEntry] = None
    try:
        cfg = await mgr.config_get(name=name, uuid=uuid)
    except NoSuchConfigError:
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    assert cfg is not None

    run_uuid = await mgr.run(cfg)
    return S3TestsRunReply(date=dt.now(), uuid=run_uuid)


@router.get("/info", response_model=S3TestsInfoReply)
async def get_s3tests_info(request: Request, uuid: UUID) -> S3TestsInfoReply:
    logger.debug(f"obtain status for uuid {uuid}.")
    return S3TestsInfoReply()


@router.get("/status", response_model=S3TestsStatusReply)
async def get_s3tests_status(
    request: Request,
    mgr: S3TestsMgr = Depends(s3tests_mgr),
) -> S3TestsStatusReply:
    return S3TestsStatusReply(running=mgr.is_running())


@router.post("/config", response_model=S3TestsConfigPostReply)
async def post_config(
    request: Request,
    desc: S3TestsConfigDesc,
    mgr: S3TestsMgr = Depends(s3tests_mgr),
) -> S3TestsConfigPostReply:
    uuid: UUID = await mgr.config_create(desc)
    return S3TestsConfigPostReply(uuid=uuid)


@router.get("/config", response_model=S3TestsConfigGetReply)
async def get_config(
    request: Request,
    name: Optional[str] = None,
    uuid: Optional[UUID] = None,
    mgr: S3TestsMgr = Depends(s3tests_mgr),
) -> S3TestsConfigGetReply:
    """
    Obtains a list of configs. If `name` or `uuid` are specified, the list will
    contain the config with said `name` or `uuid`; if such item does not exist,
    the list will be empty. Should both `name` and `uuid` be specified, `name`
    takes precedence.
    """

    lst: List[S3TestsConfigEntry] = []
    if name is not None or uuid is not None:
        try:
            config = await mgr.config_get(name=name, uuid=uuid)
            lst.append(config)
        except NoSuchConfigError:
            pass
    else:
        lst = await mgr.config_list()
    return S3TestsConfigGetReply(config=lst)