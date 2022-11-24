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
import { Component, OnDestroy, OnInit } from "@angular/core";
import {
  catchError,
  EMPTY,
  finalize,
  Observable,
  Subscription,
  take,
  timer,
} from "rxjs";
import {
  S3TestsAPIService,
  S3TestsStatusAPIResult,
} from "~/app/shared/services/api/s3tests-api.service";
import { S3TestsConfigEntry } from "~/app/shared/types/s3tests.type";

type Progress = {
  total: number;
  run: number;
  percent: number;
};

@Component({
  selector: "s3gw-s3tests",
  templateUrl: "./s3tests.component.html",
  styleUrls: ["./s3tests.component.scss"],
})
export class S3testsComponent implements OnInit, OnDestroy {
  public isBusy: boolean = false;
  public currentConfig?: S3TestsConfigEntry;
  public currentProgress?: Progress;
  public currentDuration?: number;

  private statusUpdateInterval = 1000;
  private statusSubscription?: Subscription;
  private statusRefreshTimerSubscription?: Subscription;

  public constructor(private svc: S3TestsAPIService) {}

  public ngOnInit(): void {
    this.refreshStatus();
  }

  public ngOnDestroy(): void {
    this.statusSubscription?.unsubscribe();
    this.statusRefreshTimerSubscription?.unsubscribe();
  }

  private refreshStatus(): void {
    this.statusSubscription = this.updateStatus()
      .pipe(
        catchError((err) => {
          console.error("error refreshing running status: ", err);
          return EMPTY;
        }),
        finalize(() => {
          this.statusRefreshTimerSubscription = timer(this.statusUpdateInterval)
            .pipe(take(1))
            .subscribe(() => {
              this.statusSubscription!.unsubscribe();
              this.refreshStatus();
            });
        }),
        take(1),
      )
      .subscribe((status: S3TestsStatusAPIResult) => {
        if (!status.busy) {
          this.isBusy = false;
          this.currentConfig = undefined;
          this.currentProgress = undefined;
          this.currentDuration = undefined;
        } else {
          this.isBusy = true;
          this.currentConfig = status.current!.config;
          const progress = status.current!.progress;
          const total = progress.tests_total;
          const run = progress.tests_run;
          const percent =
            Math.round(((run * 100) / total + Number.EPSILON) * 100) / 100;
          this.currentProgress = {
            total: total,
            run: run,
            percent: percent,
          };
          const startTime = new Date(status.current!.time_start).getTime();
          const now = new Date().getTime();
          this.currentDuration = (now - startTime) / 1000;
        }
      });
  }

  private updateStatus(): Observable<S3TestsStatusAPIResult> {
    return this.svc.getStatus();
  }
}
