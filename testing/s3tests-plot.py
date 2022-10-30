#!/usr/bin/env python3

# Copyright (C) 2022 SUSE, LLC
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at
# your option) any later version.

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false
# pyright: reportMissingTypeStubs=false

import asyncio
import math
import re
import sys
from io import StringIO
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import click
import pandas
import plotly.graph_objects as go
import yaml
from plotly.subplots import make_subplots


async def _parse_log(logfile: Path) -> str:

    assert logfile.exists() and logfile.is_file()
    tests: List[Tuple[str, str]] = [("unit", "result")]
    with logfile.open("r") as fd:

        regex = re.compile("^(s3tests_boto3\\..*)\\s+...\\s+(\\w+)$")

        for line in fd.readlines():
            m = re.match(regex, line)
            if m is None:
                continue
            assert len(m.groups()) == 2
            tests.append((m.group(1), m.group(2).lower()))

    res_lst: List[str] = [f"{unit}\t{res}" for unit, res in tests]
    return "\n".join(res_lst)


async def plot_s3tests(
    logpath: Path,
    filters: Dict[str, List[str]],
    destpath: Path,
    name: str,
    format: str,
) -> None:
    assert logpath.exists() and logpath.is_file()

    csv_raw = await _parse_log(logpath)
    data = pandas.read_csv(StringIO(csv_raw), sep="\t")

    # print(data.sort_values(by=["unit", "result"]))
    df = (
        data.groupby(by="result", group_keys=True)
        .count()
        .reset_index(names="result")
    )

    # fig = px.pie(
    #     df,
    #     values="unit",
    #     names="result",
    #     title="Results",
    #     color="result",
    #     color_discrete_map={
    #         "ok": "green",
    #         "fail": "orange",
    #         "error": "darkred",
    #     },
    # )
    # fig.write_image("s3tests-result.png")

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


@click.command()
@click.argument("logfile", type=click.Path(exists=True))
@click.option(
    "-c", "--config", type=click.Path(exists=True), help="Config file."
)
@click.option("-n", "--name", type=str, help="Name the chart!")
@click.option(
    "-d",
    "--dest",
    type=click.Path(file_okay=False, dir_okay=True),
    help="Destination directory for plots.",
)
@click.option(
    "-f",
    "--format",
    type=click.Choice(["png", "svg"]),
    help="Output image format.",
)
def cli(
    logfile: str,
    config: Optional[str],
    name: Optional[str],
    dest: Optional[str],
    format: Optional[str],
) -> None:

    logpath = Path(logfile)
    assert logpath.exists() and logpath.is_file()

    destpath = Path(".") if dest is None else Path(dest)
    if not destpath.exists():
        destpath.mkdir(parents=True)
    assert destpath.is_dir()

    plot_name = "s3tests" if name is None else name
    output_format = "png" if format is None else format

    filters_dict: Dict[str, List[str]] = {}

    if config is not None:
        confpath = Path(config)
        assert confpath.exists() and confpath.is_file()

        with confpath.open("r") as fd:
            try:
                raw = yaml.safe_load(fd)
                if "filters" not in raw:
                    click.echo("malformed config file.")
                    sys.exit(1)
                filters_dict = raw["filters"]
            except yaml.error.YAMLError:
                click.echo("error loading config file.")
                sys.exit(1)

        # print(filters_dict)

    asyncio.run(
        plot_s3tests(logpath, filters_dict, destpath, plot_name, output_format)
    )


if __name__ == "__main__":
    cli()
