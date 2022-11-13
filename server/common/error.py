# Copyright (C) 2022 SUSE, LLC
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at
# your option) any later version.

from typing import Optional


class ServerError(Exception):
    _msg: Optional[str]

    def __init__(self, msg: Optional[str] = None) -> None:
        self._msg = msg if msg is not None else None

    def __str__(self) -> str:
        return self.msg

    @property
    def msg(self) -> str:
        return "" if self._msg is None else self._msg
