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
import { Injectable, OnDestroy } from "@angular/core";
import {
  BehaviorSubject,
  catchError,
  EMPTY,
  finalize,
  Subscription,
  take,
  timer,
} from "rxjs";
import {
  S3TestsAPIService,
  S3TestsStatusAPIResult,
} from "~/app/shared/services/api/s3tests-api.service";
import { S3TestsCurrentRun } from "../types/s3tests.type";

export type S3TestsProgress = {
  total: number;
  done: number;
  percent: number;
};

export type S3TestsStatus =
  | {
      busy: boolean;
      lastRefreshed: Date;
      item?: S3TestsCurrentRun;
      progress?: S3TestsProgress;
    }
  | undefined;

@Injectable({
  providedIn: "root",
})
export class S3TestsStatusService implements OnDestroy {
  private statusSubject: BehaviorSubject<S3TestsStatus> =
    new BehaviorSubject<S3TestsStatus>(undefined);

  private statusUpdateInterval = 1000;
  private statusSubscription?: Subscription;
  private statusRefreshTimeSubscription?: Subscription;
  private lastStatus?: S3TestsStatus;

  public constructor(private api: S3TestsAPIService) {
    this.refreshStatus();
  }

  public ngOnDestroy(): void {
    this.statusSubscription?.unsubscribe();
    this.statusRefreshTimeSubscription?.unsubscribe();
  }

  private refreshStatus(): void {
    this.statusSubscription = this.api
      .getStatus()
      .pipe(
        catchError((err) => {
          console.error("error refreshing s3tests status: ", err);
          return EMPTY;
        }),
        finalize(() => {
          this.statusRefreshTimeSubscription = timer(this.statusUpdateInterval)
            .pipe(take(1))
            .subscribe(() => {
              this.statusSubscription!.unsubscribe();
              this.refreshStatus();
            });
        }),
        take(1),
      )
      .subscribe((res: S3TestsStatusAPIResult) => {
        const date = new Date(res.date);
        let status: S3TestsStatus;
        if (!res.busy) {
          status = { busy: false, lastRefreshed: date };
        } else {
          console.assert(!!res.current);
          const curr = res.current!;
          const progress = curr.progress;
          const total = progress.tests_total;
          const done = progress.tests_run;
          const percent =
            Math.round(((done * 100) / total + Number.EPSILON) * 100) / 100;
          status = {
            busy: true,
            lastRefreshed: date,
            item: curr,
            progress: {
              total: total,
              done: done,
              percent: percent,
            },
          };
        }
        if (!!this.lastStatus && this.lastStatus.busy == status.busy) {
          if (!status.busy) {
            // don't update subject if there's nothing to change.
            return;
          }
          if (this.lastStatus.progress!.percent == status.progress!.percent) {
            // no change in progress, don't update.
            return;
          }
        }
        this.lastStatus = status;
        this.statusSubject.next(status);
      });
  }

  public get status(): BehaviorSubject<S3TestsStatus> {
    return this.statusSubject;
  }
}
