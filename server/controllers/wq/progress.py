# Copyright (C) 2022 SUSE, LLC
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at
# your option) any later version.

from datetime import datetime as dt
from typing import Optional
from uuid import UUID
from pydantic import BaseModel

from controllers.wq.types import WQItemProgressType


class WQItemProgress(BaseModel):
    uuid: UUID
    is_running: bool
    is_done: bool
    time_start: Optional[dt]
    time_end: Optional[dt]
    duration: int
    progress: WQItemProgressType
