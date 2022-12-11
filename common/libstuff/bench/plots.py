# Copyright (C) 2022 SUSE, LLC
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at
# your option) any later version.

# pyright: reportUnknownMemberType=false

from collections import defaultdict
from typing import Dict, List, Optional
import pandas

from pydantic import BaseModel


class Histogram(BaseModel):
    op: str
    data: List[float]


class Plots:

    data: pandas.DataFrame
    _latency_histogram_per_op: Dict[str, Histogram]

    def __init__(self, json_data: str) -> None:
        self.data = pandas.read_json(json_data)
        self._latency_histogram_per_op = {}

    def get_ops(self) -> List[str]:
        return [x for x in self.data["op"].unique() if isinstance(x, str)]

    def get_latency_histogram_per_op(self) -> Dict[str, Histogram]:
        res: Dict[str, Histogram] = {}
        ops: List[str] = self.get_ops()
        for op in ops:
            h: Optional[Histogram] = self.get_latency_histogram_for_op(op)
            if h is not None:
                res[op] = h

        return res

    def get_latency_histogram_for_op(self, op: str) -> Optional[Histogram]:
        data: pandas.DataFrame = self.data.query(f"op == '{op}'")
        if data.empty:
            return None

        hist_data: pandas.Series[float] = data["duration_ms"]
        dd = hist_data.to_dict(defaultdict(list))
        return Histogram(op=op, data=list(dd.values()))
