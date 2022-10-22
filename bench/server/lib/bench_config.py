# Benchmarking the s3gw project
# Copyright (C) 2022 SUSE, LLC
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at
# your option) any later version.

from pathlib import Path
from typing import Dict, List, Optional

import yaml
from pydantic import BaseModel, ValidationError


class ConfigError(Exception):
    pass


class BenchmarkParams(BaseModel):
    num_objects: int
    object_size: str
    duration: str


class BenchmarkVolume(BaseModel):
    source: str
    target: str


class BenchmarkPorts(BaseModel):
    source: int
    target: int


class BenchmarkTarget(BaseModel):
    image: str
    args: Optional[str]
    volumes: Optional[List[BenchmarkVolume]]
    ports: Optional[List[BenchmarkPorts]]
    access_key: str
    secret_key: str
    host: str


class BenchmarkConfig(BaseModel):
    name: str
    params: BenchmarkParams
    targets: Dict[str, BenchmarkTarget]


def read_config(path: Path) -> BenchmarkConfig:
    assert path.exists()
    assert path.is_file()

    try:
        with path.open("r") as fd:
            raw = yaml.safe_load(fd)
    except yaml.error.YAMLError:
        raise ConfigError()

    try:
        res = BenchmarkConfig.parse_obj(raw)
    except ValidationError:
        raise ConfigError()

    return res
