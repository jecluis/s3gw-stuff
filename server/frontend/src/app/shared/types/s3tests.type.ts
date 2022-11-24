/*
 * Copyright 2022 SUSE, LLC
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

export type S3TestsConfig = {
  container: {
    image: string;
    ports: string[];
    volumes: string[];
  };
  tests: {
    suite: string;
    ignore: string[];
    exclude: string[];
    include: string[];
  };
};

export type S3TestsConfigDesc = {
  name: string;
  config: S3TestsConfig;
};

export type S3TestsConfigEntry = {
  uuid: string;
  desc: S3TestsConfigDesc;
};

export type S3TestsCollectedUnits = {
  all: string[];
  filtered: string[];
};

export type S3TestsConfigItem = {
  config: S3TestsConfigEntry;
  tests: S3TestsCollectedUnits;
};

export type S3TestsResultEntry = {
  uuid: string;
  time_start: string;
  time_end: string;
  config: S3TestsConfigEntry;
  results: { [id: string]: string };
  is_error: boolean;
  error_msg: string;
  progress?: {
    tests_total: number;
    tests_run: number;
  };
};

export type S3TestsCurrentRun = {
  uuid: string;
  time_start: string;
  config: S3TestsConfigEntry;
  progress: {
    tests_total: number;
    tests_run: number;
  };
};
