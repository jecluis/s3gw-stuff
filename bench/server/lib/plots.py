# Benchmarking the s3gw project
# Copyright (C) 2022 SUSE, LLC
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at
# your option) any later version.

# pyright: reportUnknownMemberType=false

from pathlib import Path
from typing import Dict, List

import pandas
import plotly.figure_factory as ff  # type: ignore


class Plots:

    destdir: Path

    def __init__(self, destdir: Path) -> None:
        self.destdir = destdir

    def plot_op_histogram(
        self, op: str, entries: Dict[str, pandas.DataFrame]
    ) -> None:
        hist_data: List[pandas.Series[float]] = []
        group_labels: List[str] = []

        for target, data in entries.items():
            hist_data.append(data["duration_ms"])  # type: ignore
            group_labels.append(target)

        fig = ff.create_distplot(hist_data, group_labels, curve_type="normal")
        fig.update_layout(
            title_text=f"{op} Latency Distribution", legend_title_text="Target"
        )
        fig.update_xaxes(title_text="milliseconds")
        fig.update_yaxes(title_text="Count")

        fig.write_image(
            self.destdir.joinpath(f"warp-distplot-{op.lower()}.png")
        )
