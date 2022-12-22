# Copyright (C) 2022 SUSE, LLC
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at
# your option) any later version.

from typing import Union
from pydantic import BaseModel

from controllers.bench.progress import BenchTargetsProgress


class WQItemProgressType(BaseModel):
    __root__: Union[BenchTargetsProgress, None]
