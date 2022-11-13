#!/usr/bin/env python3

# Copyright (C) 2022 SUSE, LLC
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at
# your option) any later version.

import logging.config
import os
from pathlib import Path
from typing import Any, Dict, Optional

from api import containers, s3tests
from common.error import ServerError
from controllers.config import ServerConfig, ServerConfigError
from controllers.context import ServerContext
from fastapi import FastAPI
from fastapi.logger import logger
from fastapi.staticfiles import StaticFiles


def setup_logging() -> None:
    level = "INFO" if not os.getenv("S3GW_SERVER_DEBUG") else "DEBUG"
    logpath = os.getenv("S3GW_SERVER_LOGDIR", Path.cwd().absolute().as_posix())
    logging_config: Dict[str, Any] = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "simple": {
                "format": (
                    "[%(levelname)-5s] %(asctime)s -- "
                    "%(module)s > %(message)s"
                ),
                "datefmt": "%Y-%m-%dT%H:%M:%S",
            },
            "colorized": {
                "()": "uvicorn.logging.ColourizedFormatter",
                "format": (
                    "%(levelprefix)s %(asctime)s -- %(module)s > %(message)s"
                ),
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
        },
        "handlers": {
            "console": {
                "level": level,
                "class": "logging.StreamHandler",
                "formatter": "colorized",
            },
            "log_file": {
                "level": "DEBUG",
                "class": "logging.handlers.RotatingFileHandler",
                "formatter": "simple",
                "filename": f"{logpath}/s3gw-server.log",
                "maxBytes": 10485760,
                "backupCount": 1,
            },
        },
        "loggers": {
            "uvicorn": {
                "level": "DEBUG",
                "handlers": ["console", "log_file"],
                "propagate": "no",
            }
        },
        "root": {"level": "DEBUG", "handlers": ["console", "log_file"]},
    }
    logging.config.dictConfig(logging_config)


async def server_startup(_: FastAPI, api: FastAPI):
    setup_logging()
    logger.info("bench startup")

    cfgfile: Optional[str] = os.getenv("S3GW_SERVER_CONFIG")
    if cfgfile is None:
        raise ServerError(
            "config file not specified through 'S3GW_SERVER_CONFIG' env."
        )
    cfgpath = Path(cfgfile)
    if not cfgpath.exists():
        raise ServerError(f"config file at '{cfgpath}' does not exist.")
    if not cfgpath.is_file():
        raise ServerError(f"{cfgpath} is not a file.")

    try:
        cfg = ServerConfig.parse(cfgpath)
    except ServerConfigError as e:
        logger.error(f"unable to read config file at '{cfgpath}: {e.msg}")
        raise ServerError("unable to read config.")

    api.state.ctx = ServerContext(cfg)
    await api.state.ctx.start()


async def server_shutdown(_: FastAPI, api: FastAPI):
    logger.info("bench shutdown")
    await api.state.ctx.stop()


def server_factory(
    startup=server_startup,  # type: ignore
    shutdown=server_shutdown,  # type: ignore
    static_path: Optional[Path] = None,
):
    api_tags_metadata = [
        {
            "name": "status",
            "description": "Overall server status",
        },
        {
            "name": "containers",
            "description": "Containers information",
        },
        {
            "name": "s3tests",
            "description": "Run S3Tests and obtain results",
        },
    ]

    server_app = FastAPI(docs_url=None)
    server_api = FastAPI(
        title="s3gw stuff",
        description="Helps doing stuff to s3gw.",
        version="0.1.0",
        openapi_tags=api_tags_metadata,
    )

    @server_app.on_event("startup")  # type: ignore
    async def on_startup():  # type: ignore
        await startup(server_app, server_api)

    @server_app.on_event("shutdown")  # type: ignore
    async def on_shutdown():  # type: ignore
        await shutdown(server_app, server_api)

    server_api.include_router(containers.router)
    server_api.include_router(s3tests.router)

    # bench_api.include_router(whatever.router)
    server_app.mount("/api", server_api, name="api")
    if static_path:
        server_app.mount(
            "/", StaticFiles(directory=static_path, html=True), name="static"
        )
    return server_app


def app_factory():
    static_path = Path(__file__).absolute().parent.joinpath("static")
    static: Optional[Path] = None
    if static_path.exists() and static_path.is_dir():
        static = static_path

    return server_factory(server_startup, server_shutdown, static)
