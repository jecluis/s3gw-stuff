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
import {
  BehaviorSubject,
  catchError,
  EMPTY,
  finalize,
  map,
  Observable,
  Subscription,
  take,
  timer,
} from "rxjs";
import { ServerAPIService } from "~/app/shared/services/api/server-api.service";
import { S3TestsConfigEntry } from "../types/s3tests.type";
import { BenchConfigEntry, BenchProgress } from "./api/bench-api.service";

export enum WorkQueueEntryKind {
  None = 0,
  Bench = 1,
  S3Tests = 2,
}

export type WorkQueueEntry = {
  uuid: string;
  kind: WorkQueueEntryKind;
  is_running: boolean;
  is_done: boolean;
  time_start?: string;
  time_end?: string;
  duration: number;
};

export type WorkQueueState = {
  waiting: WorkQueueEntry[];
  finished: WorkQueueEntry[];
  current?: WorkQueueEntry;
};

export type S3TestsProgress = {
  tests_total: number;
  tests_run: number;
};

export type WorkQueueProgress = {
  uuid: string;
  is_running: boolean;
  is_done: boolean;
  time_start: string;
  time_end: string;
  duration: number;
  progress: BenchProgress | S3TestsProgress;
};

export type WorkQueueStatusEntry = {
  item: WorkQueueEntry;
  progress: WorkQueueProgress;
  config: BenchConfigEntry | S3TestsConfigEntry;
};

export type WorkQueueStatus = {
  is_running: boolean;
  current?: WorkQueueStatusEntry;
};

type WorkQueueStateAPIResult = {
  status: WorkQueueState;
};

type WorkQueueStatusAPIResult = {
  status: WorkQueueStatus;
};

@Injectable({
  providedIn: "root",
})
export class WorkQueueService {
  private statusSubject: BehaviorSubject<WorkQueueStatus> =
    new BehaviorSubject<WorkQueueStatus>({ is_running: false });

  private statusRefreshInterval: number = 1000;
  private statusRefreshSubscription?: Subscription;
  private statusSubscription?: Subscription;

  public constructor(private svc: ServerAPIService) {
    this.refreshStatus();
  }

  public getWorkQueue(): Observable<WorkQueueState> {
    return this.svc.get<WorkQueueStateAPIResult>("/workqueue/").pipe(
      take(1),
      catchError((err) => {
        console.error("Error obtaining work queue: ", err);
        return EMPTY;
      }),
      map((res: WorkQueueStateAPIResult) => res.status),
    );
  }

  private refreshStatus(): void {
    this.statusSubscription = this.svc
      .get<WorkQueueStatusAPIResult>("/workqueue/status")
      .pipe(
        take(1),
        catchError((err) => {
          console.error("error obtaining workqueue status: ", err);
          return EMPTY;
        }),
        finalize(() => {
          this.statusRefreshSubscription = timer(this.statusRefreshInterval)
            .pipe(
              take(1),
              finalize(() => {
                this.statusRefreshSubscription!.unsubscribe();
              }),
            )
            .subscribe(() => {
              this.statusSubscription!.unsubscribe();
              this.refreshStatus();
            });
        }),
        map((res: WorkQueueStatusAPIResult) => res.status),
      )
      .subscribe((status: WorkQueueStatus) => {
        this.statusSubject.next(status);
      });
  }

  public get status(): BehaviorSubject<WorkQueueStatus> {
    return this.statusSubject;
  }
}
