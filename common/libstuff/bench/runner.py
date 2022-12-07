# Copyright (C) 2022 SUSE, LLC
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at
# your option) any later version.

import asyncio
import logging
import random
import string
from typing import Dict, List, Optional

from pydantic import BaseModel

from libstuff import podman
from libstuff.bench.warp import WarpBenchmark, ProgressCB


class BenchmarkRunningError(Exception):
    pass


class BenchmarkParams(BaseModel):
    num_objects: int
    object_size: str
    duration: str


class BenchmarkVolume(BaseModel):
    source: str
    target: str


class BenchmarkPorts(BaseModel):
    source: int
    target: int


class BenchmarkTarget(BaseModel):
    image: str
    args: Optional[str]
    volumes: Optional[List[BenchmarkVolume]]
    ports: Optional[List[BenchmarkPorts]]
    access_key: str
    secret_key: str
    host: str


class BenchmarkConfig(BaseModel):
    name: str
    params: BenchmarkParams
    targets: Dict[str, BenchmarkTarget]


class BenchmarkRunner:
    name: str
    params: BenchmarkParams
    logger: logging.Logger

    lock: asyncio.Lock
    is_running: bool
    target_cid: Optional[str]

    def __init__(
        self,
        name: str,
        params: BenchmarkParams,
        logger: logging.Logger = logging.getLogger(),
    ) -> None:
        self.name = name
        self.params = params
        self.logger = logger
        self.lock = asyncio.Lock()
        self.is_running = False
        self.target_cid = None

    async def run(
        self,
        name: str,
        target: BenchmarkTarget,
        progress_cb: Optional[ProgressCB] = None,
    ) -> str:
        async with self.lock:
            if self.is_running:
                self.logger.debug(f"already running, cid: {self.target_cid}")
                raise BenchmarkRunningError()
            self.is_running = True

        await self._run_target(name, target)
        # wait for target to become available
        # this should be a test on the target's address
        await asyncio.sleep(10)  # for now give it 10 seconds
        res = await self._run_warp(target, progress_cb)
        await self._stop_target()
        return res

    async def _run_target(self, name: str, target: BenchmarkTarget) -> None:

        volumes: List[str] = []
        ports: List[str] = []

        if target.volumes is not None:
            volumes = [f"{v.source}:{v.target}" for v in target.volumes]
        if target.ports is not None:
            ports = [f"{p.source}:{p.target}" for p in target.ports]

        args: Optional[List[str]] = None
        if target.args is not None:
            args = target.args.split()

        rnd = "".join(random.choice(string.ascii_letters) for _ in range(6))
        instance_name = f"{self.name}-{name}-{rnd}"

        self.target_cid = await podman.run(
            target.image,
            name=instance_name,
            args=args,
            ports=ports,
            volumes=volumes,
            pull_if_newer=True,
        )

    async def _monitor_target(self) -> None:
        pass

    async def _stop_target(self) -> None:
        async with self.lock:
            if not self.is_running:
                self.logger.error("attempting to stop target, but not running.")
                return
            await podman.stop(id=self.target_cid)
            self.is_running = False
            self.target_cid = None

    async def _run_warp(
        self, target: BenchmarkTarget, progress_cb: Optional[ProgressCB]
    ) -> str:
        warp = WarpBenchmark(
            self.params.object_size,
            self.params.num_objects,
            self.params.duration,
            self.logger,
        )
        res = await warp.run(
            target.host,
            target.access_key,
            target.secret_key,
            progress_cb,
        )
        return res
