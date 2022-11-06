#!/usr/bin/env python3

# Copyright (C) 2022 SUSE, LLC
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at
# your option) any later version.

import asyncio
import sys
from datetime import datetime as dt
from pathlib import Path
from typing import List, Optional, Tuple

import click
import yaml
from libstuff import git
from libstuff.s3tests import plots
from libstuff.s3tests.runner import (
    ContainerConfig,
    S3TestsConfig,
    S3TestsRunner,
)
from pydantic import ValidationError


def clone_s3tests(dest: Path) -> bool:
    assert not dest.exists()
    try:
        git.clone("https://github.com/ceph/s3-tests", dest)
    except git.GitError as e:
        click.echo(f"error: {e}")
        return False
    assert dest.exists()
    return True


def plot(
    name: str, results: List[Tuple[str, str]], plotsconf: plots.PlotsConfig
) -> None:
    import pandas

    df = pandas.DataFrame(results, columns=["unit", "result"])
    print(df)
    print(results)
    destpath = plotsconf.output_path
    if not destpath.exists():
        destpath.mkdir(parents=True)
    assert destpath.exists()
    assert destpath.is_dir()
    respath = plots.plot_s3test_results(
        df,
        plotsconf.filters,
        destpath,
        name,
        plotsconf.output_format,
    )
    print(respath)


async def main(
    suite: str,
    name: str,
    config: ContainerConfig,
    s3testsconf: S3TestsConfig,
    s3tests: Path,
    plotsconf: plots.PlotsConfig,
) -> None:

    runner = S3TestsRunner(name, suite, s3tests, config, s3testsconf)
    results: List[Tuple[str, str]] = await runner.run()
    plot(name, results, plotsconf)


@click.command()
@click.argument("suite", type=str)
@click.option("-n", "--name", type=str, help="This run's name.")
@click.option(
    "-c",
    "--config",
    type=click.Path(file_okay=True, dir_okay=False, exists=True),
    help="Config file.",
    required=True,
)
@click.option(
    "--s3tests",
    type=click.Path(dir_okay=True, file_okay=False, exists=False),
    help="s3tests directory.",
)
def cli(
    suite: str,
    name: Optional[str],
    config: str,
    s3tests: Optional[str],
) -> None:

    confpath = Path(config)
    if not confpath.exists():
        click.echo("missing config file.")
        sys.exit(1)
    if not confpath.is_file():
        click.echo("config path is not a file.")
        sys.exit(1)

    s3testsconf = S3TestsConfig(ignore=[], exclude=[], include=[])
    plotsconf = plots.PlotsConfig(
        filters={}, output_path=Path("."), output_format="png"
    )

    with confpath.open("r") as fd:
        try:
            rawconf = yaml.safe_load(fd)
            if "container" not in rawconf:
                click.echo("malformed config file.")
                sys.exit(1)
            try:
                containerconf = ContainerConfig.parse_obj(rawconf["container"])
            except ValidationError:
                click.echo("malformed container config.")
                sys.exit(1)

            if "s3tests" in rawconf:
                try:
                    s3testsconf = S3TestsConfig.parse_obj(rawconf["s3tests"])
                except ValidationError:
                    click.echo("malformed s3tests config.")
                    sys.exit(1)

            if "plots" in rawconf:
                try:
                    plotsconf = plots.PlotsConfig.parse_obj(rawconf["plots"])
                except ValidationError:
                    click.echo("malformed plots config.")
                    sys.exit(1)

        except yaml.error.YAMLError:
            click.echo("error loading config file.")
            sys.exit(1)

    print(f"container conf: {containerconf}")
    print(f"s3tests conf: {s3testsconf}")

    tnow = dt.now().isoformat(timespec="seconds")
    testname: str = name if name is not None else f"s3tests-{tnow}"
    print(testname)

    s3testspath = (
        Path(s3tests) if s3tests is not None else Path("./s3tests.git")
    )
    if s3testspath.exists() and not s3testspath.is_dir():
        click.echo(
            "s3tests path at '{s3testspath}' exists and is not a directory."
        )
        sys.exit(1)
    elif not s3testspath.exists():
        if not clone_s3tests(s3testspath):
            click.echo(f"unable to clone s3tests to '{s3testspath}'.")
            sys.exit(1)

    assert s3testspath.exists() and s3testspath.is_dir()
    asyncio.run(
        main(
            suite, testname, containerconf, s3testsconf, s3testspath, plotsconf
        )
    )


if __name__ == "__main__":
    cli()
