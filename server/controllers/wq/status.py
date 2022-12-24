# Copyright (C) 2022 SUSE, LLC
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at
# your option) any later version.

from datetime import datetime as dt
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel

from controllers.wq.progress import WQItemProgress
from controllers.wq.types import (
    WQItemConfigType,
    WQItemKind,
)


class WorkQueueStatusItem(BaseModel):
    uuid: UUID
    kind: WQItemKind
    is_running: bool
    is_done: bool
    time_start: Optional[dt]
    time_end: Optional[dt]
    duration: int


class WorkQueueStatusEntry(BaseModel):
    item: WorkQueueStatusItem
    progress: WQItemProgress
    config: WQItemConfigType


class WorkQueueState(BaseModel):
    waiting: List[WorkQueueStatusItem]
    finished: List[WorkQueueStatusItem]
    current: Optional[WorkQueueStatusItem]


class WorkQueueStatus(BaseModel):
    is_running: bool
    current: Optional[WorkQueueStatusEntry]
