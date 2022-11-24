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
import { Injectable } from "@angular/core";
import { Observable } from "rxjs";
import { ServerAPIService } from "~/app/shared/services/api/server-api.service";
import {
  S3TestsConfigDesc,
  S3TestsConfigItem,
  S3TestsCurrentRun,
  S3TestsResultEntry,
} from "~/app/shared/types/s3tests.type";

export type S3TestsConfigAPIResult = {
  date: Date;
  entries: S3TestsConfigItem[];
};

export type S3TestsConfigAPIPostResult = {
  date: string;
  uuid: string;
};

export type S3TestsResultsAPIResult = {
  date: Date;
  results: { [id: string]: S3TestsResultEntry };
};

export type S3TestsStatusAPIResult = {
  date: string;
  busy: boolean;
  current?: S3TestsCurrentRun;
};

@Injectable({
  providedIn: "root",
})
export class S3TestsAPIService {
  public constructor(private svc: ServerAPIService) {}

  public getConfig(): Observable<S3TestsConfigAPIResult> {
    return this.svc.get<S3TestsConfigAPIResult>("/s3tests/config");
  }

  public postConfig(
    desc: S3TestsConfigDesc,
  ): Observable<S3TestsConfigAPIPostResult> {
    return this.svc.post<S3TestsConfigAPIPostResult>("/s3tests/config", desc);
  }

  public getResults(): Observable<S3TestsResultsAPIResult> {
    return this.svc.get<S3TestsResultsAPIResult>("/s3tests/results");
  }

  public getStatus(): Observable<S3TestsStatusAPIResult> {
    return this.svc.get<S3TestsStatusAPIResult>("/s3tests/status");
  }
}
