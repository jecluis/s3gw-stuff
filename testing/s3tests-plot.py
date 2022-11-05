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
import re
import sys
from io import StringIO
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import click
import pandas
import yaml
from lib import plots


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
    plots.plot_s3test_results(data, filters, destpath, name, format)


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
