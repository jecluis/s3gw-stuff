# Benchmarking the s3gw project
# Copyright (C) 2022 SUSE, LLC
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at
# your option) any later version.

from datetime import datetime as dt
from typing import Any, Dict, List

from pydantic import BaseModel, parse_obj_as


class WarpResultSSRequests(BaseModel):
    obj_size: int
    requests: int
    dur_avg_millis: int
    dur_median_millis: int
    dur_90_millis: int
    dur_99_millis: int
    fastest_millis: int
    slowest_millis: int
    dur_percentiles_millis: List[int]


class WarpResultSegment(BaseModel):
    bytes_per_sec: int
    obj_per_sec: float
    start: dt


class WarpResultSegmentInfo(BaseModel):
    segment_duration_millis: int
    sorted_by: str
    segments: List[WarpResultSegment]
    fastest_start: dt
    fastest_bps: int
    fastest_ops: int
    median_start: dt
    median_bps: int
    median_ops: int
    slowest_start: dt
    slowest_bps: int
    slowest_ops: int


class WarpResultThroughput(BaseModel):
    errors: int
    measure_duration_millis: int
    start_time: dt
    end_time: dt
    average_bps: int
    average_ops: float
    operations: int
    segmented: WarpResultSegmentInfo


class WarpResultOperation(BaseModel):
    type: str
    n: int
    start_time: dt
    end_time: dt
    concurrency: int
    single_sized_requests: WarpResultSSRequests
    errors: int
    throughput: WarpResultThroughput


def parse_warp_result(raw_dict: Dict[str, Any]) -> List[WarpResultOperation]:
    assert "operations" in raw_dict
    return parse_obj_as(List[WarpResultOperation], raw_dict["operations"])
