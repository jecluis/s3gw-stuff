#!/usr/bin/env python3

# Copyright (C) 2022 SUSE, LLC
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at
# your option) any later version.

import asyncio
import re
import sys
from datetime import datetime as dt
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import click
import yaml
from libstuff import git, podman
from pydantic import BaseModel, Field, ValidationError

from lib import plots


class S3TestsError(Exception):
    pass


class ContainerConfig(BaseModel):
    image: str
    ports: List[str] = Field([])
    volumes: List[str] = Field([])


class S3TestsConfig(BaseModel):
    ignore: List[str] = Field([])
    exclude: List[str] = Field([])
    include: List[str] = Field([])


class PlotsConfig(BaseModel):
    filters: Dict[str, List[str]] = Field({})
    output_path: Path = Field(Path("."))
    output_format: str = Field("png")


def clone_s3tests(dest: Path) -> bool:
    assert not dest.exists()
    try:
        git.clone("https://github.com/ceph/s3-tests", dest)
    except git.GitError as e:
        click.echo(f"error: {e}")
        return False
    assert dest.exists()
    return True


async def _s3tests_collect(suite: str, cmd: List[str]) -> List[str]:
    collected_tests: List[str] = []

    async def _gather_tests(reader: asyncio.StreamReader) -> None:
        regex = re.compile(f"^{suite}\\.(test_[\\w\\d_-]+) ... \\w+.*$")
        async for line in reader:
            l = line.decode("utf-8")
            m = re.match(regex, l)
            if m is None:
                continue
            assert len(m.groups()) == 1
            t = m.group(1)
            assert len(t) > 0
            assert t.startswith("test_")
            collected_tests.append(t)

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    assert proc.stdout is not None
    assert proc.stderr is not None
    await asyncio.gather(_gather_tests(proc.stdout), _gather_tests(proc.stderr))

    retcode = await proc.wait()
    if retcode != 0:
        # print((await proc.stderr.read()).decode("utf-8"))
        raise S3TestsError()

    return collected_tests


def _s3tests_prepare(
    suite: str, collected: List[str], exclude: List[str], include: List[str]
) -> List[str]:
    def _apply_filters(
        lst: List[str], filters: List[str], *, exclude: bool
    ) -> List[str]:

        regex: List[re.Pattern[str]] = [re.compile(f) for f in filters]
        results: List[str] = []

        for entry in lst:
            test_name = f"{suite}.{entry}"
            matched = False
            for f in regex:
                m = re.fullmatch(f, test_name)
                if m is not None:
                    matched = True
                    break
            if matched and exclude:
                continue
            elif not matched and not exclude:
                continue

            results.append(entry)
        return results

    tests = collected.copy()
    print(f"num tests: {len(tests)}")
    if len(include) > 0:
        tests = _apply_filters(tests, include, exclude=False)
        print(f"after include: {len(tests)}")
    if len(exclude) > 0:
        tests = _apply_filters(tests, exclude, exclude=True)
        print(f"after exclude: {len(tests)}")
    return tests


async def _s3tests_run(
    suite: str, base_cmd: List[str], tests: List[str]
) -> List[Tuple[str, str]]:
    results: List[Tuple[str, str]] = []

    async def _capture_result(reader: asyncio.StreamReader) -> None:
        regex = re.compile(f"^{suite}\\.(test_[\\w\\d_-]+)\\s+...\\s+(\\w+).*$")
        async for line in reader:
            l = line.decode("utf-8")
            m = re.match(regex, l)
            if m is None:
                continue
            assert len(m.groups()) == 2
            test = m.group(1)
            res = m.group(2)
            assert test.startswith("test_")
            results.append((test, res.lower()))
            progress = len(results) * 100 / len(tests)
            print(f"progress: {progress}%")

        print("finished")

    cmd = base_cmd + tests
    proc = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    assert proc.stdout is not None
    assert proc.stderr is not None
    await asyncio.gather(
        _capture_result(proc.stdout), _capture_result(proc.stderr)
    )
    await proc.wait()
    return results


async def run_s3tests(
    s3testsconf: S3TestsConfig,
    suite: str,
    name: str,
    s3tests: Path,
    plotsconf: PlotsConfig,
) -> None:

    base_cmd = [
        "bash",
        "./run-s3tests-helper.sh",
        "--host",
        "127.0.0.1",
        "--port",
        "7480",
        "--path",
        s3tests.as_posix(),
        "--suite",
        suite,
    ]

    collect_cmd = base_cmd + ["--collect"]
    collected_tests = await _s3tests_collect(suite, collect_cmd)
    filtered_tests = _s3tests_prepare(
        suite, collected_tests, s3testsconf.exclude, s3testsconf.include
    )

    print(f"collected {len(collected_tests)} tests")
    nfiltered = len(collected_tests) - len(filtered_tests)
    print(f"filtered {nfiltered} tests for a total of {len(filtered_tests)}")

    if len(filtered_tests) == 0:
        print("no tests to run.")
        return

    results = await _s3tests_run(suite, base_cmd, filtered_tests)

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
    plotsconf: PlotsConfig,
) -> None:

    # try:
    #     cid = await podman.run(
    #         config.image, ports=config.ports, volumes=config.volumes
    #     )
    # except podman.PodmanError:
    #     click.echo(f"unable to start container image '{config.image}'.")
    #     sys.exit(1)

    await run_s3tests(s3testsconf, suite, name, s3tests, plotsconf)

    pass


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
    plotsconf = PlotsConfig(
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
                    plotsconf = PlotsConfig.parse_obj(rawconf["plots"])
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
