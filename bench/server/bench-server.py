#!/usr/bin/env python3

# Benchmarking the s3gw project
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

from fastapi import FastAPI
from fastapi.logger import logger
from fastapi.staticfiles import StaticFiles


def setup_logging() -> None:
    level = "INFO" if not os.getenv("BENCH_DEBUG") else "DEBUG"
    logpath = os.getenv("BENCH_LOGDIR", Path.cwd().absolute().as_posix())
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
                "filename": f"{logpath}/bench-server.log",
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


async def bench_startup(_: FastAPI, api: FastAPI):
    setup_logging()
    logger.info("bench startup")
    pass


async def bench_shutdown(_: FastAPI, api: FastAPI):
    logger.info("bench shutdown")
    pass


def bench_factory(
    startup=bench_startup,  # type: ignore
    shutdown=bench_shutdown,  # type: ignore
    static_path: Optional[Path] = None,
):
    api_tags_metadata = [
        {
            "name": "status",
            "description": "Overall server status",
        },
    ]

    bench_app = FastAPI(docs_url=None)
    bench_api = FastAPI(
        title="Benchmarking s3gw",
        description="Helps benchmarking and keeping track of results for s3gw.",
        version="0.1.0",
        openapi_tags=api_tags_metadata,
    )

    @bench_app.on_event("startup")  # type: ignore
    async def on_startup():  # type: ignore
        await startup(bench_app, bench_api)

    @bench_app.on_event("shutdown")  # type: ignore
    async def on_shutdown():  # type: ignore
        await shutdown(bench_app, bench_api)

    # bench_api.include_router(whatever.router)
    bench_app.mount("/api", bench_api, name="api")
    if static_path:
        bench_app.mount(
            "/", StaticFiles(directory=static_path, html=True), name="static"
        )
    return bench_app


def app_factory():
    static_path = Path(__file__).absolute().parent.joinpath("static")
    static: Optional[Path] = None
    if static_path.exists() and static_path.is_dir():
        static = static_path

    return bench_factory(bench_startup, bench_shutdown, static)
