# Copyright (C) 2022 SUSE, LLC
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at
# your option) any later version.

from pydantic import BaseModel


class S3TestRunProgress(BaseModel):
    tests_total: int
    tests_run: int

    @property
    def progress(self) -> float:
        if self.tests_total == 0:
            return 100
        return (self.tests_run * 100) / self.tests_total
