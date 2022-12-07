# Copyright (C) 2022 SUSE, LLC
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at
# your option) any later version.

import asyncio
import logging
import random
import re
import shutil
import string
import tempfile
from enum import Enum
from pathlib import Path
from typing import Callable, List, Optional

import pandas
import zstandard as zstd
from pydantic import BaseModel


class WarpBenchmarkState(Enum):
    NONE = 0
    PREPARING = 1
    RUNNING = 2
    DONE = 3


ProgressCB = Callable[[WarpBenchmarkState, float], None]


class WarpError(Exception):
    pass


class WarpNotFoundError(WarpError):
    pass


class WarpOperationResult(BaseModel):
    name: str
    mbps: float
    objps: float


class WarpResult(BaseModel):
    put: WarpOperationResult
    get: WarpOperationResult
    delete: WarpOperationResult
    stat: WarpOperationResult


class WarpBenchmark:
    logger: logging.Logger
    objsize: str
    numobjs: int
    duration: str

    state: WarpBenchmarkState
    progress: float

    def __init__(
        self,
        objsize: str,
        numobjs: int,
        duration: str,
        logger: logging.Logger = logging.getLogger(),
    ) -> None:

        self.logger = logger

        found = shutil.which("warp") is not None
        if not found:
            self.logger.error("unable to find 'warp' command.")
            raise WarpNotFoundError()

        self.objsize = objsize
        self.numobjs = numobjs
        self.duration = duration
        self.state = WarpBenchmarkState.NONE
        self.progress = 0.0

    async def run(
        self,
        host: str,
        access_key: str,
        secret_key: str,
        progress_cb: Optional[ProgressCB] = None,
    ) -> str:

        bucketname = "".join(
            random.choice(string.ascii_lowercase) for _ in range(16)
        )
        self.logger.info(f"run warp on bucket {bucketname}")
        tmp_benchdata_dir = Path(tempfile.mkdtemp())
        tmp_benchdata_file = tmp_benchdata_dir.joinpath("warp-result")
        cmd: List[str] = [
            "warp",
            "mixed",
            # "--quiet",
            # "--json",
            "--no-color",
            "--benchdata",
            tmp_benchdata_file.as_posix(),
            "--host",
            host,
            "--access-key",
            access_key,
            "--secret-key",
            secret_key,
            "--obj.size",
            self.objsize,
            "--objects",
            str(self.numobjs),
            "--duration",
            self.duration,
            "--noclear",
            "--bucket",
            bucketname,
        ]
        self.logger.debug(f"run warp cmd: {cmd}")
        proc = await asyncio.subprocess.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        assert proc.stdout is not None
        await asyncio.gather(self._process_output(proc.stdout, progress_cb))
        retcode = await proc.wait()
        if retcode != 0:
            assert proc.stderr is not None
            err = (await proc.stderr.read()).decode("utf-8")
            self.logger.error(f"error running warp: {err}")
            raise WarpError()

        result = self.parse_csv(tmp_benchdata_file)
        for dirent in tmp_benchdata_dir.iterdir():
            dirent.unlink()
        tmp_benchdata_dir.rmdir()
        return result

    def parse_csv(self, datafile: Path) -> str:
        zstd_file = datafile.with_suffix(".csv.zst")
        csv_file = datafile.with_suffix(".csv")
        assert zstd_file.exists()
        with zstd_file.open("rb") as source:
            decomp = zstd.ZstdDecompressor()
            with csv_file.open("wb") as dest:
                decomp.copy_stream(source, dest)

        assert csv_file.exists()
        self.logger.debug(f"reading csv file at {csv_file}")
        data = pandas.read_csv(csv_file, delimiter="\t")  # type: ignore
        self.logger.debug(data)
        data["duration_ms"] = data.apply(  # type: ignore
            lambda r: r["duration_ns"] * 1e-6, axis=1  # type: ignore
        )
        return data.to_json()  # type: ignore

    async def _process_output(
        self,
        reader: asyncio.StreamReader,
        progress_cb: Optional[ProgressCB] = None,
    ) -> List[str]:
        def _handle_progress(line: str) -> bool:
            res = re.match("Preparing:.*\\s([\\d+.]+)%.*", line)
            if res is not None:
                assert len(res.groups()) == 1
                self.state = WarpBenchmarkState.PREPARING
                self.progress = float(res.group(1))
                if self.progress % 10 == 0:
                    self.logger.debug(f"preparing: {self.progress}%")

                if progress_cb is not None:
                    progress_cb(self.state, self.progress)

                return True
            res = re.match("Benchmarking:.*\\s([\\d+.]+)%.*", line)
            if res is not None:
                assert len(res.groups()) == 1
                self.state = WarpBenchmarkState.RUNNING
                self.progress = float(res.group(1))
                if self.progress % 10 == 0:
                    self.logger.debug(f"benchmarking: {self.progress}%")

                if progress_cb is not None:
                    progress_cb(self.state, self.progress)

                return True
            return False

        def _is_warp_output(line: str) -> bool:
            res = re.match("warp:.*", line)
            if res is not None:
                return True
            return False

        lines: List[str] = []
        cur_line: bytearray = bytearray()
        while not reader.at_eof():
            b = await reader.read(1)
            if len(b) == 0:
                # at eof
                break
            if b == b"\r" or b == b"\n":
                # end of line
                line = cur_line.decode("utf-8")
                cur_line = bytearray()
                if len(line.strip()) == 0:
                    continue
                if _is_warp_output(line):
                    continue
                if _handle_progress(line):
                    continue
                lines.append(line)
                self.logger.debug(line)
            else:
                cur_line.extend(b)
        return lines
