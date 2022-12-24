# Copyright (C) 2022 SUSE, LLC
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at
# your option) any later version.

from enum import Enum
from typing import Union

from controllers.bench.progress import BenchTargetsProgress
from controllers.s3tests.progress import S3TestRunProgress
from pydantic import BaseModel

from controllers.bench.config import BenchConfigDesc
from controllers.s3tests.config import S3TestsConfigEntry


class WQItemProgressType(BaseModel):
    __root__: Union[BenchTargetsProgress, S3TestRunProgress]


class WQItemConfigType(BaseModel):
    __root__: Union[BenchConfigDesc, S3TestsConfigEntry]


class WQItemKind(Enum):
    NONE = 0
    BENCH = 1
    S3TESTS = 2
