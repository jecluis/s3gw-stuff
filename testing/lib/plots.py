# Copyright (C) 2022 SUSE, LLC
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at
# your option) any later version.

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false
# pyright: reportMissingTypeStubs=false

import math
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def plot_s3test_results(
    data: pandas.DataFrame,
    filters: Dict[str, List[str]],
    destpath: Path,
    name: str,
    format: str,
) -> Path:

    df = (
        data.groupby(by="result", group_keys=True)
        .count()
        .reset_index(names="result")
    )

    filtered: Dict[str, pandas.DataFrame] = {}
    for k, filter_lst in filters.items():
        k_df: Optional[pandas.DataFrame] = None
        for filter in filter_lst:
            filter_df = data[data["unit"].str.match(filter)]
            if filter_df.empty:
                continue
            if k_df is None:
                k_df = filter_df
            else:
                k_df = pandas.concat([k_df, filter_df], verify_integrity=True)
        if k_df is None:
            print(f"unable to find matching units for section '{k}'")
            continue
        filtered[k] = k_df

    # max 4 plots per row
    nplots = len(filtered)
    nrows = math.ceil(nplots / 4)
    ncols = 4 if nplots >= 4 else nplots
    ncols = 1 if ncols == 0 else ncols
    totals_spec: List[Any] = [{"colspan": ncols, "type": "domain"}] + [
        None for _ in range(ncols - 1)
    ]
    specs: List[List[Optional[Dict[str, Any]]]] = [totals_spec]
    for _ in range(nrows):
        specs.append([{"type": "domain"} for _ in range(ncols)])

    result_colors = {
        "ok": "yellowgreen",
        "fail": "tomato",
        "error": "slategray",
    }

    fig = make_subplots(
        rows=nrows + 1,
        cols=ncols,
        specs=specs,
        subplot_titles=["total"] + list(filtered.keys()),
    )
    # default height: 450px, ballpark height for one row: 225px
    fig.update_layout(height=max(450, (nrows + 1) * 225), title_text=name)

    total_labels: List[str] = []
    total_values: List[str] = []
    for l, v in df.values:
        total_labels.append(l)
        total_values.append(v)
    fig.add_trace(
        go.Pie(labels=total_labels, values=total_values, name="total"), 1, 1
    )

    col = 1
    row = 2
    for k, df in filtered.items():
        if col > 4:
            row += 1
            col = 1

        section_data = (
            df.groupby(by="result").count().reset_index(names="result")
        )
        # print(section_data)
        # print(f"labels: {section_data.index}, values: {section_data.values}")
        labels: List[str] = []
        values: List[int] = []
        for l, v in section_data.values:
            labels.append(l)
            values.append(v)

        marker_colors = section_data["result"].map(result_colors)
        pie = go.Pie(
            labels=labels,
            values=values,
            name=k,
            textinfo="percent+value",
            marker_colors=marker_colors,
        )
        fig.add_trace(pie, row, col)
        col += 1

    destfilename = name.lower().replace(" ", "-")
    destfile = destpath.joinpath(f"{destfilename}-total.{format}")
    fig.write_image(destfile)
    return destfile
