# Copyright (C) 2022 SUSE, LLC
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at
# your option) any later version.

import asyncio
import re
from pathlib import Path
from typing import List, Optional, Tuple

from libstuff import podman
from pydantic import BaseModel, Field

_HELPER_FILE = "run-s3tests-helper.sh"


def _get_helper_path() -> Path:
    p = Path(__file__).resolve().parent
    helper = p.joinpath(_HELPER_FILE)
    assert helper.exists()
    assert helper.is_file()
    return helper


class S3TestsError(Exception):
    pass


class RunnerError(Exception):
    _msg: Optional[str]

    def __init__(self, msg: Optional[str] = None) -> None:
        self._msg = msg

    def __str__(self) -> str:
        return "" if self._msg is None else self._msg

    @property
    def msg(self) -> str:
        return "" if self._msg is None else self._msg


class ContainerConfig(BaseModel):
    image: str
    ports: List[str] = Field([])
    volumes: List[str] = Field([])


class TestsConfig(BaseModel):
    ignore: List[str] = Field([])
    exclude: List[str] = Field([])
    include: List[str] = Field([])


class S3TestsRunner:
    name: str
    suite: str
    s3testspath: Path
    containerconf: ContainerConfig
    s3testsconf: TestsConfig

    cid: Optional[str]
    s3tests_proc: Optional[asyncio.subprocess.Process]
    s3tests_done: bool
    s3tests_killed: bool

    def __init__(
        self,
        name: str,
        suite: str,
        s3tests: Path,
        containerconf: ContainerConfig,
        s3testsconf: TestsConfig,
    ) -> None:
        self.name = name
        self.suite = suite
        self.s3testspath = s3tests
        self.containerconf = containerconf
        self.s3testsconf = s3testsconf

        self.cid = None
        self.s3tests_proc = None
        self.s3tests_done = False
        self.s3tests_killed = False

    async def run(self) -> List[Tuple[str, str]]:
        cconf = self.containerconf
        try:
            self.cid = await podman.run(
                cconf.image,
                ports=cconf.ports,
                volumes=cconf.volumes,
                pull_if_newer=True,
            )
        except podman.PodmanError:
            raise RunnerError(
                f"unable to start container image '{cconf.image}'."
            )

        results, success = await asyncio.gather(
            self._run_s3tests(), self._monitor_container()
        )
        if not success:
            print("container died while running the tests!")

        try:
            await podman.stop(id=self.cid)
        except podman.PodmanError:
            raise RunnerError(f"unable to stop container '{self.cid}'.")

        return results

    async def _monitor_container(self) -> bool:
        success = True
        assert self.cid is not None

        while not self.s3tests_done:
            if self.s3tests_proc is None:
                # probably hasn't started yet
                await asyncio.sleep(1.0)
                continue

            is_running = await podman.is_running(self.cid)
            if not is_running:
                print("container died!!")
                assert self.s3tests_proc.stderr is not None
                assert self.s3tests_proc.stdout is not None
                self.s3tests_killed = True
                self.s3tests_proc.terminate()
                # workaround for https://bugs.python.org/issue43884
                self.s3tests_proc._transport.close()  # type: ignore
                success = False
                break

            await asyncio.sleep(1.0)

        return success

    async def _run_s3tests(self) -> List[Tuple[str, str]]:
        base_cmd = [
            "bash",
            _get_helper_path().as_posix(),
            "--host",
            "127.0.0.1",
            "--port",
            "7480",
            "--path",
            self.s3testspath.as_posix(),
            "--suite",
            self.suite,
        ]

        collect_cmd = base_cmd + ["--collect"]
        collected_tests = await self._s3tests_collect(self.suite, collect_cmd)
        filtered_tests = self._s3tests_prepare(
            self.suite,
            collected_tests,
            self.s3testsconf.exclude,
            self.s3testsconf.include,
        )

        print(f"collected {len(collected_tests)} tests")
        nfiltered = len(collected_tests) - len(filtered_tests)
        print(
            f"filtered {nfiltered} tests for a total of {len(filtered_tests)}"
        )

        if len(filtered_tests) == 0:
            print("no tests to run.")
            return []

        results = await self._s3tests_run(self.suite, base_cmd, filtered_tests)
        self.s3tests_done = True
        return results

    async def _s3tests_collect(self, suite: str, cmd: List[str]) -> List[str]:
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
        await asyncio.gather(
            _gather_tests(proc.stdout), _gather_tests(proc.stderr)
        )

        retcode = await proc.wait()
        if retcode != 0:
            # print((await proc.stderr.read()).decode("utf-8"))
            raise S3TestsError()

        return collected_tests

    def _s3tests_prepare(
        self,
        suite: str,
        collected: List[str],
        exclude: List[str],
        include: List[str],
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
        self, suite: str, base_cmd: List[str], tests: List[str]
    ) -> List[Tuple[str, str]]:
        results: List[Tuple[str, str]] = []

        async def _capture_result(reader: asyncio.StreamReader) -> None:
            regex = re.compile(
                f"^{suite}\\.(test_[\\w\\d_-]+)\\s+...\\s+(\\w+).*$"
            )
            async for line in reader:
                if self.s3tests_killed:
                    break

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
        self.s3tests_proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        assert self.s3tests_proc.stdout is not None
        assert self.s3tests_proc.stderr is not None
        await asyncio.gather(
            _capture_result(self.s3tests_proc.stdout),
            _capture_result(self.s3tests_proc.stderr),
        )
        await self.s3tests_proc.wait()
        return results
