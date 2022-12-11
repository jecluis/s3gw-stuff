# Copyright (C) 2022 SUSE, LLC
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at
# your option) any later version.

from datetime import datetime as dt
from typing import Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel
from libstuff.bench.runner import BenchmarkParams
from libstuff.bench.warp import WarpBenchmarkState


class BenchTarget(BaseModel):
    image: str
    args: Optional[str]
    port: int
    access_key: str
    secret_key: str


class BenchConfig(BaseModel):
    name: str
    params: BenchmarkParams
    targets: Dict[str, BenchTarget]


class BenchConfigDesc(BaseModel):
    uuid: UUID
    config: BenchConfig


class TargetProgress(BaseModel):
    name: str
    state: WarpBenchmarkState
    value: float
    has_progress: bool
    is_running: bool
    is_done: bool
    is_error: bool
    error_str: Optional[str]
    time_start: Optional[dt]
    time_end: Optional[dt]
    duration: int

    def progress_cb(self, state: WarpBenchmarkState, value: float) -> None:
        self.has_progress = True
        self.state = state
        self.value = value


class BenchProgress(BaseModel):
    is_running: bool
    is_done: bool
    time_start: Optional[dt]
    time_end: Optional[dt]
    duration: int
    targets: List[TargetProgress]


class BenchTargetError(BaseModel):
    target: str
    error_str: str


class BenchResult(BaseModel):
    uuid: UUID
    progress: BenchProgress
    is_error: bool
    errors: List[BenchTargetError]
    config: BenchConfig
    results: Dict[str, str]


class BenchDBNS:
    # keep bench's database namespaces
    NS_CONFIG_BY_UUID = "bench-config"
    NS_CONFIG_BY_NAME = "bench-config-by-name"
    NS_RESULTS = "bench-results"
    NS_CONFIG_RESULTS = "bench-config-results"
