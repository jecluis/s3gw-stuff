# Copyright (C) 2022 SUSE, LLC
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at
# your option) any later version.

from datetime import datetime as dt
from typing import List, Optional
from pydantic import BaseModel
from libstuff.bench.warp import WarpBenchmarkState


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


class BenchTargetsProgress(BaseModel):
    targets: List[TargetProgress]
