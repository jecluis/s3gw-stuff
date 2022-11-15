# Copyright (C) 2022 SUSE, LLC
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at
# your option) any later version.

from __future__ import annotations

from pathlib import Path

import yaml
from common.error import ServerError
from pydantic import BaseModel, ValidationError


class ServerConfigError(ServerError):
    pass


class ServerConfig(BaseModel):
    pass

    @staticmethod
    def parse(conffile: Path) -> ServerConfig:
        assert conffile.exists()
        assert conffile.is_file()

        with conffile.open("r") as fd:
            try:
                rawconf = yaml.safe_load(fd)
            except yaml.error.YAMLError:
                raise ServerConfigError("error loading config file.")

            try:
                conf = ServerConfig.parse_obj(rawconf)
            except ValidationError:
                raise ServerConfigError("malformed config file.")

            return conf
