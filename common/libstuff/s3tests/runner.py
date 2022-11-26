# Copyright (C) 2022 SUSE, LLC
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at
# your option) any later version.

import asyncio
import logging
import re
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from libstuff import podman
from pydantic import BaseModel, Field

_HELPER_FILE = "run-s3tests-helper.sh"

ProgressCB = Callable[[int, int], None]


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
    target_port: int


class TestsConfig(BaseModel):
    suite: str = Field("s3tests_boto3.functional")
    ignore: List[str] = Field([])
    exclude: List[str] = Field([])
    include: List[str] = Field([])


class CollectedTests(BaseModel):
    all: List[str]
    filtered: List[str]


class ContainerRunConfig(BaseModel):
    name: str
    host_port: int
    config: ContainerConfig


class ErrorTestResult(BaseModel):
    name: str
    trace: List[str]
    log: List[str]


class TestRunResult(BaseModel):
    results: List[Tuple[str, str]]
    errors: Dict[str, ErrorTestResult]


class S3TestsRunner:
    name: str
    s3testspath: Path

    logger: logging.Logger

    cid: Optional[str]
    s3tests_proc: Optional[asyncio.subprocess.Process]
    s3tests_done: bool
    s3tests_killed: bool

    def __init__(
        self,
        name: str,
        s3tests: Path,
        logger: logging.Logger = logging.getLogger(),
    ) -> None:
        self.name = name
        self.s3testspath = s3tests

        self.cid = None
        self.s3tests_proc = None
        self.s3tests_done = False
        self.s3tests_killed = False

        self.logger = logger

    async def run(
        self,
        containerconf: ContainerRunConfig,
        s3testsconf: TestsConfig,
        progress_cb: Optional[ProgressCB] = None,
    ) -> TestRunResult:
        crconf = containerconf
        cconf = containerconf.config
        ports: List[str] = [f"{crconf.host_port}:{cconf.target_port}"]
        try:
            self.cid = await podman.run(
                cconf.image,
                ports=ports,
                pull_if_newer=True,
            )
        except podman.PodmanError:
            self.logger.error("unable to start container image.")
            raise RunnerError(
                f"unable to start container image '{cconf.image}'."
            )

        results, success = await asyncio.gather(
            self._run_s3tests(containerconf, s3testsconf, progress_cb),
            self._monitor_container(),
        )
        if not success:
            self.logger.error("container died while running the tests!")

        try:
            await podman.stop(id=self.cid)
        except podman.PodmanError:
            self.logger.error(f"unable to stop container '{self.cid}'.")
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
                self.logger.error("container died!!")
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

    def _get_cmd(
        self,
        s3testsconf: TestsConfig,
        *,
        port: int = 7480,
        collect: bool = False,
    ) -> List[str]:
        cmd: List[str] = [
            "bash",
            _get_helper_path().as_posix(),
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--path",
            self.s3testspath.as_posix(),
            "--suite",
            s3testsconf.suite,
        ]
        if collect:
            cmd.append("--collect")

        return cmd

    async def collect(self, s3testsconf: TestsConfig) -> CollectedTests:
        collect_cmd = self._get_cmd(s3testsconf, collect=True)
        collected_tests = await self._s3tests_collect(
            s3testsconf.suite, collect_cmd
        )
        filtered_tests = self._s3tests_prepare(
            s3testsconf.suite,
            collected_tests,
            s3testsconf.exclude,
            s3testsconf.include,
        )
        return CollectedTests(all=collected_tests, filtered=filtered_tests)

    async def _run_s3tests(
        self,
        containerconf: ContainerRunConfig,
        s3testsconf: TestsConfig,
        progress_cb: Optional[ProgressCB] = None,
    ) -> TestRunResult:
        self.logger.debug("running s3tests")
        run_cmd = self._get_cmd(
            s3testsconf, port=containerconf.host_port, collect=False
        )

        collected = await self.collect(s3testsconf)
        self.logger.debug(f"collected {len(collected.all)} tests")
        nfiltered = len(collected.all) - len(collected.filtered)
        self.logger.debug(
            f"filtered {nfiltered} tests for a total of "
            f"{len(collected.filtered)}"
        )

        if len(collected.filtered) == 0:
            self.logger.info("no tests to run.")
            return TestRunResult(results=[], errors={})

        self.logger.debug(f"running {len(collected.filtered)}")
        results = await self._s3tests_run(
            s3testsconf.suite, run_cmd, collected.filtered, progress_cb
        )
        self.s3tests_done = True
        return results

    async def _s3tests_collect(self, suite: str, cmd: List[str]) -> List[str]:
        collected_tests: List[str] = []

        async def _gather_tests(reader: asyncio.StreamReader) -> None:
            regex = re.compile(f"^{suite}.*\\.(test_[\\w\\d_-]+) ... \\w+.*$")
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
            self.logger.error("error collecting tests.")
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
        self.logger.debug(f"num tests: {len(tests)}")
        if len(include) > 0:
            tests = _apply_filters(tests, include, exclude=False)
            self.logger.debug(f"after include: {len(tests)}")
        if len(exclude) > 0:
            tests = _apply_filters(tests, exclude, exclude=True)
            self.logger.debug(f"after exclude: {len(tests)}")
        return tests

    async def _s3tests_run(
        self,
        suite: str,
        base_cmd: List[str],
        tests: List[str],
        progress_cb: Optional[ProgressCB] = None,
    ) -> TestRunResult:
        results: List[Tuple[str, str]] = []
        errors: Dict[str, ErrorTestResult] = {}

        def _progress_cb(progress: int) -> None:
            if progress_cb is None:
                return
            progress_cb(len(tests), progress)

        def _handle_test_summary(m: re.Match[str]) -> None:
            assert len(m.groups()) == 2
            test = m.group(1)
            res = m.group(2)
            assert test.startswith("test_")
            results.append((test, res.lower()))
            progress = len(results) * 100 / len(tests)
            self.logger.debug(f"progress: {progress}%")
            _progress_cb(len(results))

        async def _handle_test_result(
            reader: asyncio.StreamReader,
        ) -> ErrorTestResult:
            regex_header_end = re.compile("^-+$")
            regex_test_name = re.compile(
                f"^[a-zA-Z]+:\\s+{suite}.*\\.(test_.*)$"
            )
            regex_body_start = re.compile(
                "^-+ >> begin captured logging << -+$"
            )
            regex_body_end = re.compile("^-+ >> end captured logging << -+$")
            test_name: Optional[str] = None

            line = (await reader.readline()).decode("utf-8").strip("\n")
            m = re.match(regex_test_name, line)
            # self.logger.debug(f"header: line: {line}")
            # self.logger.debug(f"header: test: {m}")
            assert m is not None
            assert len(m.groups()) == 1
            test_name = m.group(1)
            assert test_name is not None

            line = (await reader.readline()).decode("utf-8").strip("\n")
            assert re.match(regex_header_end, line) is not None

            trace: List[str] = []
            body: List[str] = []

            in_body = False
            in_trace = True
            async for line in reader:
                l = line.decode("utf-8").strip("\n")
                if re.match(regex_body_start, l) is not None:
                    in_body = True
                    in_trace = False
                    continue
                if re.match(regex_body_end, l) is not None:
                    break
                if in_trace:
                    assert not in_body
                    trace.append(l)
                elif in_body:
                    assert not in_trace
                    body.append(l)

            return ErrorTestResult(name=test_name, trace=trace, log=body)

        async def _capture_result(reader: asyncio.StreamReader) -> None:
            test_regex = re.compile(
                f"^{suite}.*\\.(test_[\\w\\d_-]+)\\s+...\\s+(\\w+).*$"
            )
            result_regex_header_start = re.compile("^=+$")

            async for line in reader:
                if self.s3tests_killed:
                    break

                l = line.decode("utf-8").strip("\n")
                # self.logger.debug(f">> {l}")

                m = re.match(test_regex, l)
                if m is not None:
                    _handle_test_summary(m)
                    continue

                m = re.match(result_regex_header_start, l)
                if m is not None:
                    try:
                        result = await _handle_test_result(reader)
                    except Exception as e:
                        self.logger.error(e)
                        break
                    assert result is not None
                    errors[result.name] = result
                    continue

            self.logger.debug("finished capturing results.")

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
        return TestRunResult(results=results, errors=errors)
