# Copyright (C) 2022 SUSE, LLC
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at
# your option) any later version.

from uuid import UUID

from libstuff.s3tests.runner import ContainerConfig, TestsConfig
from common.error import ServerError
from pydantic import BaseModel


class S3TestsConfigError(ServerError):
    pass


class S3TestsConfig(BaseModel):
    container: ContainerConfig
    tests: TestsConfig


class S3TestsConfigDesc(BaseModel):
    name: str
    config: S3TestsConfig


class S3TestsConfigEntry(BaseModel):
    uuid: UUID
    desc: S3TestsConfigDesc
