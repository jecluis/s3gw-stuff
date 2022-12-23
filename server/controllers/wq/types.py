# Copyright (C) 2022 SUSE, LLC
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at
# your option) any later version.

from datetime import datetime as dt
from enum import Enum
from typing import List, Optional, Union
from uuid import UUID

from controllers.bench.progress import BenchTargetsProgress
from controllers.s3tests.progress import S3TestRunProgress
from pydantic import BaseModel


class WQItemProgressType(BaseModel):
    __root__: Union[BenchTargetsProgress, S3TestRunProgress]


class WQItemKind(Enum):
    NONE = 0
    BENCH = 1
    S3TESTS = 2


class WorkQueueStatusItem(BaseModel):
    uuid: UUID
    kind: WQItemKind
    is_running: bool
    is_done: bool
    time_start: Optional[dt]
    time_end: Optional[dt]
    duration: int


class WorkQueueStatus(BaseModel):
    waiting: List[WorkQueueStatusItem]
    finished: List[WorkQueueStatusItem]
    current: Optional[WorkQueueStatusItem]
