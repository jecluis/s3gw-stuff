# Benchmarking the s3gw project
# Copyright (C) 2022 SUSE, LLC
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at
# your option) any later version.

import asyncio
import json
import random
import re
import shutil
import string
import tempfile
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional

import pandas
import zstandard as zstd
from pydantic import BaseModel


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
    objsize: str
    numobjs: int
    duration: str

    class State(Enum):
        NONE = 0
        PREPARING = 1
        RUNNING = 2
        DONE = 3

    state: State
    progress: float

    def __init__(self, objsize: str, numobjs: int, duration: str) -> None:

        found = shutil.which("warp") is not None
        if not found:
            raise WarpNotFoundError()

        self.objsize = objsize
        self.numobjs = numobjs
        self.duration = duration
        self.state = WarpBenchmark.State.NONE
        self.progress = 0.0

    async def run(self, host: str, access_key: str, secret_key: str) -> str:

        bucketname = "".join(
            random.choice(string.ascii_lowercase) for _ in range(16)
        )
        print(f"run warp on bucket {bucketname}")
        tmp_benchdata_dir = Path(tempfile.mkdtemp())
        tmp_benchdata_file = tmp_benchdata_dir.joinpath("warp-result")
        cmd: List[str] = [
            "warp",
            "mixed",
            "--quiet",
            "--json",
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
        print(f"run warp cmd: {cmd}")
        proc = await asyncio.subprocess.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        retcode = await proc.wait()
        if retcode != 0:
            raise WarpError()

        result = self.parse_csv(tmp_benchdata_file)
        for dirent in tmp_benchdata_dir.iterdir():
            dirent.unlink()
        tmp_benchdata_dir.rmdir()
        return result

        assert proc.stdout
        assert proc.stderr
        res = await asyncio.gather(self._process_output(proc.stdout))
        stdout: List[str] = res[0]

        retcode = await proc.wait()
        if retcode != 0:
            assert proc.stderr is not None
            print((await proc.stderr.read()).decode("utf-8"))
            raise WarpError()

        json_raw_lst: List[str] = []
        in_json = False
        for l in stdout:
            if not in_json:
                if l.strip() == "{":
                    in_json = True
                else:
                    continue
            json_raw_lst.append(l)

        json_raw = "".join(json_raw_lst)
        json_dict = json.loads(json_raw)
        with Path("./warp-result.json").open("w+") as fd:
            json.dump(json_dict, fd)

        print(json_dict)
        raise WarpError()

        print("finished warp")
        res = self._parse(stdout)
        assert "DELETE" in res
        assert "GET" in res
        assert "PUT" in res
        assert "STAT" in res
        return WarpResult(
            put=res["PUT"],
            get=res["GET"],
            delete=res["DELETE"],
            stat=res["STAT"],
        )

    def parse_csv(self, datafile: Path) -> str:
        zstd_file = datafile.with_suffix(".csv.zst")
        csv_file = datafile.with_suffix(".csv")
        assert zstd_file.exists()
        with zstd_file.open("rb") as source:
            decomp = zstd.ZstdDecompressor()
            with csv_file.open("wb") as dest:
                decomp.copy_stream(source, dest)

        assert csv_file.exists()
        data = pandas.read_csv(csv_file)  # type: ignore
        data["duration_ms"] = data.apply(  # type: ignore
            lambda r: r["duration_ns"] * 1e-6, axis=1  # type: ignore
        )
        return data.to_json()  # type: ignore

    async def _process_output(self, reader: asyncio.StreamReader) -> List[str]:
        def _handle_progress(line: str) -> bool:
            res = re.match("Preparing:.*\\s([\\d+.]+)%.*", line)
            if res is not None:
                assert len(res.groups()) == 1
                self.state = WarpBenchmark.State.PREPARING
                self.progress = float(res.group(1))
                if self.progress % 10 == 0:
                    print(f"preparing: {self.progress}%")
                return True
            res = re.match("Benchmarking:.*\\s([\\d+.]+)%.*", line)
            if res is not None:
                assert len(res.groups()) == 1
                self.state = WarpBenchmark.State.RUNNING
                self.progress = float(res.group(1))
                if self.progress % 10 == 0:
                    print(f"benchmarking: {self.progress}%")
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
                print(line)
            else:
                cur_line.extend(b)
        return lines

    def _parse(self, lines: List[str]) -> Dict[str, WarpOperationResult]:
        def _parse_objps(v: str) -> float:
            m = re.match("([\\d.]+) obj/s", v)
            assert m is not None
            assert len(m.groups()) == 1
            return float(m.group(1))

        def _parse_mbps(v: str) -> float:
            m = re.match("([\\d.]+) ([\\w]+)/s", v)
            assert m is not None
            assert len(m.groups()) == 2
            value = float(m.group(1))
            units = m.group(2)
            if units == "MiB":
                return value
            elif units == "KiB":
                return value / 1024
            elif units == "B":
                return value / 1024**2
            elif units == "GiB":
                return value * 1024
            raise WarpError()

        in_operation = False
        operations: Dict[str, WarpOperationResult] = {}
        cur_operation: Optional[str] = None
        for line in lines:
            if line.startswith("Operation:"):
                res = re.match("Operation:[\\s]+([\\w]+),.*", line)
                assert res is not None
                assert len(res.groups()) == 1
                in_operation = True
                cur_operation = res.group(1)
                continue
            elif in_operation:
                objps = 0.0
                mbps = 0.0

                res = re.match(".*Throughput: (.*)", line)
                assert res is not None
                parts = res.group(1).split(",")
                assert len(parts) > 0
                if len(parts) == 1:
                    # only got obj/s
                    objps = _parse_objps(parts[0].strip())
                else:
                    mbps = _parse_mbps(parts[0].strip())
                    objps = _parse_objps(parts[1].strip())
                in_operation = False
                assert cur_operation is not None
                operations[cur_operation] = WarpOperationResult(
                    name=cur_operation, mbps=mbps, objps=objps
                )
                continue

        return operations
