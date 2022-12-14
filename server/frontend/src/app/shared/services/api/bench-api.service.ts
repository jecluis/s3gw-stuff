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
import { catchError, EMPTY, map, Observable, take } from "rxjs";
import { ServerAPIService } from "~/app/shared/services/api/server-api.service";

export type BenchConfigParams = {
  num_objects: number;
  object_size: string;
  duration: string;
};

export type BenchConfigTarget = {
  image: string;
  args?: string[];
  port: number;
  access_key: string;
  secret_key: string;
};

export type BenchConfig = {
  name: string;
  params: BenchConfigParams;
  targets: { [id: string]: BenchConfigTarget };
};

export type BenchConfigEntry = {
  uuid: string;
  config: BenchConfig;
};

export type BenchTargetError = {
  target: string;
  error_str: string;
};

export type BenchTargetProgress = {
  name: string;
  state: number;
  value: number;
  has_progress: boolean;
  is_running: boolean;
  is_done: boolean;
  is_error: boolean;
  error_str?: string;
  time_start?: string;
  time_end?: string;
  duration: number;
};

export type BenchProgress = {
  targets: BenchTargetProgress[];
};

export type BenchProgressEntry = {
  is_running: boolean;
  is_done: boolean;
  time_start?: string;
  time_end?: string;
  duration: number;
  progress: BenchProgress;
};

export type BenchResultTargetItem = {
  name: string;
  ops: string[];
};

export type BenchResult = {
  uuid: string;
  progress: BenchProgressEntry;
  is_error: boolean;
  errors: BenchTargetError[];
  config: BenchConfig;
  ops: BenchResultTargetItem[];
};

export type BenchResultMap = { [id: string]: BenchResult };

export type BenchRunDesc = {
  config: BenchConfigEntry;
  progress: BenchProgress;
};

export type Histogram = {
  op: string;
  data: number[];
};

export type ResultHistogramMap = { [id: string]: Histogram };
export type ResultHistograms = { [id: string]: ResultHistogramMap };

type BenchGetConfigAPIResult = {
  date: string;
  entries: BenchConfigEntry[];
};

type BenchGetResultsAPIResult = {
  date: string;
  results: BenchResultMap;
};

type BenchGetResultsHistogramsAPIResult = {
  date: string;
  results: ResultHistograms;
};

type BenchPostConfigAPIResult = {
  date: string;
  uuid: string;
};

type BenchPostRunAPIResult = {
  date: string;
  uuid: string;
};

export type BenchGetStatusAPIResult = {
  date: string;
  available: boolean;
  busy: boolean;
  current?: BenchRunDesc;
};

@Injectable({
  providedIn: "root",
})
export class BenchAPIService {
  public constructor(private svc: ServerAPIService) {}

  public getConfig(): Observable<BenchConfigEntry[]> {
    return this.svc.get<BenchGetConfigAPIResult>("/bench/config").pipe(
      catchError((err) => {
        console.error("error obtaining bench configs.");
        return EMPTY;
      }),
      take(1),
      map((res: BenchGetConfigAPIResult) => res.entries),
    );
  }

  public getResults(): Observable<BenchResultMap> {
    return this.svc.get<BenchGetResultsAPIResult>("/bench/results").pipe(
      take(1),
      map((res: BenchGetResultsAPIResult) => res.results),
    );
  }

  public getResultsHistograms(uuid: string): Observable<ResultHistograms> {
    return this.svc
      .get<BenchGetResultsHistogramsAPIResult>("/bench/results/histograms", {
        params: { uuid: uuid },
      })
      .pipe(
        take(1),
        catchError((err) => {
          console.error("error obtaining result histograms for ", uuid);
          return EMPTY;
        }),
        map((res: BenchGetResultsHistogramsAPIResult) => res.results),
      );
  }

  public postConfig(config: BenchConfig): Observable<string> {
    return this.svc
      .post<BenchPostConfigAPIResult>("/bench/config", {
        body: config,
      })
      .pipe(
        take(1),
        map((res: BenchPostConfigAPIResult) => res.uuid),
      );
  }

  public getStatus(): Observable<BenchGetStatusAPIResult> {
    return this.svc.get<BenchGetStatusAPIResult>("/bench/status").pipe(take(1));
  }

  public runConfig(uuid: string): Observable<string> {
    return this.svc
      .post<BenchPostRunAPIResult>("/bench/run", {
        params: { uuid: uuid },
      })
      .pipe(
        take(1),
        map((res: BenchPostConfigAPIResult) => res.uuid),
      );
  }
}
