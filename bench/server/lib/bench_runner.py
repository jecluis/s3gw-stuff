# Benchmarking the s3gw project
# Copyright (C) 2022 SUSE, LLC
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at
# your option) any later version.


import asyncio
import random
import string
from typing import List, Optional

from lib.bench_config import BenchmarkParams, BenchmarkTarget
from lib.warp.warp import WarpBenchmark
from libstuff import podman


class BenchmarkRunner:
    name: str
    params: BenchmarkParams
    target: BenchmarkTarget

    is_running: bool
    instance_name: Optional[str]
    target_cid: Optional[str]

    def __init__(
        self, name: str, params: BenchmarkParams, target: BenchmarkTarget
    ) -> None:
        self.name = name
        self.params = params
        self.target = target
        self.is_running = False
        self.instance_name = None
        self.target_cid = None

    async def run(self) -> str:
        await self._run_target()
        # wait for target to become available
        # this should be a test on the target's address
        await asyncio.sleep(10)  # for now give it 10 seconds
        res = await self._run_warp()
        await self._stop_target()
        return res

    async def _run_target(self) -> None:

        volumes: List[str] = []
        ports: List[str] = []

        if self.target.volumes is not None:
            volumes = [f"{v.source}:{v.target}" for v in self.target.volumes]
        if self.target.ports is not None:
            ports = [f"{p.source}:{p.target}" for p in self.target.ports]

        args: Optional[List[str]] = None
        if self.target.args is not None:
            args = self.target.args.split()

        rnd = "".join(random.choice(string.ascii_letters) for _ in range(6))
        self.instance_name = f"{self.name}-{rnd}"

        self.target_cid = await podman.run(
            self.target.image,
            name=self.instance_name,
            args=args,
            ports=ports,
            volumes=volumes,
        )

    async def _monitor_target(self) -> None:
        pass

    async def _stop_target(self) -> None:
        await podman.stop(id=self.target_cid)

    async def _run_warp(self) -> str:
        warp = WarpBenchmark(
            self.params.object_size,
            self.params.num_objects,
            self.params.duration,
        )
        res = await warp.run(
            self.target.host, self.target.access_key, self.target.secret_key
        )
        return res
