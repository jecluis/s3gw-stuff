# Benchmarking the s3gw project
# Copyright (C) 2022 SUSE, LLC
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at
# your option) any later version.

import asyncio
from datetime import datetime as dt
from typing import List, Optional

from pydantic import BaseModel, Field, parse_raw_as


class PodmanError(Exception):
    pass


class PodmanImageName(BaseModel):
    name: str
    tag: str


class PodmanImage(BaseModel):
    id: str
    size: int
    names: List[PodmanImageName]
    created: dt
    containers: int


class _RawPodmanImage(BaseModel):
    Id: str
    Size: int
    Containers: int = Field(default=0)
    Dangling: bool = Field(default=False)
    Names: List[str] = Field(default=[])
    CreatedAt: dt


class PodmanContainerPort(BaseModel):
    host_ip: str
    container_port: int
    host_port: int
    range: int
    protocol: str


class PodmanContainer(BaseModel):
    command: Optional[List[str]]
    created: dt
    started: dt
    exited: dt
    running: bool
    state: str
    id: str
    image_id: str
    image_name: PodmanImageName
    names: List[str]


class _RawPodmanContainer(BaseModel):
    Command: Optional[List[str]]
    Created: dt
    StartedAt: dt
    Exited: bool
    ExitedAt: dt
    ExitCode: int
    State: str
    Id: str
    Image: str
    ImageID: str
    Mounts: List[str]
    Names: List[str]
    Networks: List[str]
    Ports: Optional[List[PodmanContainerPort]]


class PodmanInspectResult(BaseModel):
    id: str
    created_at: dt
    running: bool
    status: str
    started_at: dt
    finished_at: dt
    image_name: str


class _RawPodmanInspectResultState(BaseModel):
    Status: str
    Running: bool
    StartedAt: dt
    FinishedAt: dt


class _RawPodmanInspectResult(BaseModel):
    Id: str
    Created: dt
    State: _RawPodmanInspectResultState
    ImageName: str


async def list_images() -> List[PodmanImage]:

    cmd = ["podman", "images", "--format", "json"]
    proc = await asyncio.subprocess.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    retcode = await proc.wait()
    if retcode != 0:
        raise PodmanError()

    assert proc.stdout is not None
    stdout = (await proc.stdout.read()).decode("utf-8")
    raw: List[_RawPodmanImage] = parse_raw_as(List[_RawPodmanImage], stdout)

    images: List[PodmanImage] = []
    for entry in raw:
        if entry.Dangling:
            continue

        img_names: List[PodmanImageName] = []
        for name in entry.Names:
            n, tag = name.split(":")
            img_names.append(PodmanImageName(name=n, tag=tag))

        images.append(
            PodmanImage(
                id=entry.Id,
                size=entry.Size,
                names=img_names,
                created=entry.CreatedAt,
                containers=entry.Containers,
            )
        )

    return images


async def ps() -> List[PodmanContainer]:
    cmd = ["podman", "ps", "--all", "--format", "json"]
    proc = await asyncio.subprocess.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    retcode = await proc.wait()
    if retcode != 0:
        raise PodmanError()

    assert proc.stdout is not None
    stdout = (await proc.stdout.read()).decode("utf-8")
    raw: List[_RawPodmanContainer] = parse_raw_as(
        List[_RawPodmanContainer], stdout
    )

    containers: List[PodmanContainer] = []
    for entry in raw:
        n, t = entry.Image.split(":")
        image_name = PodmanImageName(name=n, tag=t)
        containers.append(
            PodmanContainer(
                command=entry.Command,
                created=entry.Created,
                started=entry.StartedAt,
                exited=entry.ExitedAt,
                running=(not entry.Exited),
                state=entry.State,
                id=entry.Id,
                image_id=entry.ImageID,
                image_name=image_name,
                names=entry.Names,
            )
        )
    return containers


async def run(
    image: str,
    *,
    name: Optional[str] = None,
    args: Optional[List[str]] = None,
    replace: bool = False,
    ports: List[str] = [],
    volumes: List[str] = [],
    pull_if_newer: bool = False,
) -> str:

    # we do not support running attached.

    volumes_cmd: List[str] = []
    ports_cmd: List[str] = []

    for vol in volumes:
        volumes_cmd.extend(["-v", vol])
    for p in ports:
        ports_cmd.extend(["-p", p])

    name_cmd: List[str] = []
    if name is not None:
        name_cmd.extend(["--name", name])
        if replace:
            name_cmd.append("--replace")

    args_cmd: List[str] = args if args is not None else []
    base_cmd = ["podman", "run", "-d"]

    if pull_if_newer:
        base_cmd.append("--pull=newer")

    cmd = base_cmd + volumes_cmd + ports_cmd + name_cmd + [image] + args_cmd

    proc = await asyncio.subprocess.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    retcode = await proc.wait()
    if retcode != 0:
        assert proc.stderr is not None
        print((await proc.stderr.read()).decode("utf-8"))
        raise PodmanError()

    assert proc.stdout is not None
    stdout = (await proc.stdout.read()).decode("utf-8")
    out_lines = stdout.splitlines()
    assert len(out_lines) > 0
    if len(out_lines) > 1:
        assert replace is True
        return out_lines[1]
    return out_lines[0]


async def inspect(id: str) -> PodmanInspectResult:
    cmd = ["podman", "inspect", id, "--format", "json"]
    proc = await asyncio.subprocess.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    retcode = await proc.wait()
    if retcode != 0:
        raise PodmanError()

    assert proc.stdout is not None
    stdout = (await proc.stdout.read()).decode("utf-8")
    raw: List[_RawPodmanInspectResult] = parse_raw_as(
        List[_RawPodmanInspectResult], stdout
    )
    assert len(raw) == 1
    res = raw[0]
    return PodmanInspectResult(
        id=res.Id,
        created_at=res.Created,
        running=res.State.Running,
        status=res.State.Status,
        started_at=res.State.StartedAt,
        finished_at=res.State.FinishedAt,
        image_name=res.ImageName,
    )


async def stop(*, id: Optional[str] = None, name: Optional[str] = None) -> None:
    target = None
    if id is not None:
        target = id
    elif name is not None:
        target = name
    else:
        assert 0 == "must provide id or name"

    assert target is not None
    cmd = ["podman", "stop", target]
    proc = await asyncio.subprocess.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL,
    )
    retcode = await proc.wait()
    if retcode != 0:
        raise PodmanError()


async def is_running(id: str) -> bool:
    res = await inspect(id)
    return res.running
