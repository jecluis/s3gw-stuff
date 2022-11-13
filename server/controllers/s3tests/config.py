# Copyright (C) 2022 SUSE, LLC
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at
# your option) any later version.

from libstuff.s3tests.plots import PlotsConfig
from libstuff.s3tests.runner import ContainerConfig, TestsConfig
from pydantic import BaseModel


class S3TestsConfig(BaseModel):
    container: ContainerConfig
    tests: TestsConfig
    plots: PlotsConfig
