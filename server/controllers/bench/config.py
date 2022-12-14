# Copyright (C) 2022 SUSE, LLC
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at
# your option) any later version.

from typing import Dict, Optional
from uuid import UUID

from libstuff.bench.runner import BenchmarkParams
from pydantic import BaseModel


class BenchTarget(BaseModel):
    image: str
    args: Optional[str]
    port: int
    access_key: str
    secret_key: str


class BenchConfig(BaseModel):
    name: str
    params: BenchmarkParams
    targets: Dict[str, BenchTarget]


class BenchConfigDesc(BaseModel):
    uuid: UUID
    config: BenchConfig
