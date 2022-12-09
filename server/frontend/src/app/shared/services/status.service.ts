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
import { S3TestsCurrentRun } from "~/app/shared/types/s3tests.type";
import {
  BenchAPIService,
  BenchGetStatusAPIResult,
  BenchRunDesc,
} from "~/app/shared/services/api/bench-api.service";
import {
  S3TestsAPIService,
  S3TestsStatusAPIResult,
} from "~/app/shared/services/api/s3tests-api.service";
import {
  BehaviorSubject,
  catchError,
  EMPTY,
  finalize,
  forkJoin,
  Subscription,
  take,
  timer,
} from "rxjs";

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

export type BenchStatus =
  | {
      running: boolean;
      busy: boolean;
      item?: BenchRunDesc;
    }
  | undefined;

type LastStatus = {
  s3tests?: S3TestsStatus;
  bench?: BenchStatus;
};

@Injectable({
  providedIn: "root",
})
export class StatusService implements OnDestroy {
  private busySubject: BehaviorSubject<boolean> = new BehaviorSubject<boolean>(
    false,
  );
  private s3testsSubject: BehaviorSubject<S3TestsStatus> =
    new BehaviorSubject<S3TestsStatus>(undefined);
  private benchSubject: BehaviorSubject<BenchStatus> =
    new BehaviorSubject<BenchStatus>(undefined);

  private statusUpdateInterval = 1000;
  private refreshSubscription?: Subscription;
  private statusSubscription?: Subscription;
  private lastStatus: LastStatus = {};

  public constructor(
    private s3testsSvc: S3TestsAPIService,
    private benchSvc: BenchAPIService,
  ) {
    this.refresh();
  }

  public ngOnDestroy(): void {
    this.refreshSubscription?.unsubscribe();
    this.statusSubscription?.unsubscribe();
  }

  private refresh(): void {
    this.statusSubscription = forkJoin({
      s3testsSvc: this.s3testsSvc.getStatus().pipe(
        catchError(() => {
          console.error("error obtaining s3tests status!");
          return EMPTY;
        }),
      ),
      bench: this.benchSvc.getStatus().pipe(
        catchError(() => {
          console.error("error obtaining bench status!");
          return EMPTY;
        }),
      ),
    })
      .pipe(
        catchError((err) => {
          console.error("error obtaining current status!");
          return EMPTY;
        }),
        finalize(() => {
          this.refreshSubscription = timer(this.statusUpdateInterval)
            .pipe(take(1))
            .subscribe(() => {
              this.statusSubscription!.unsubscribe();
              this.refresh();
            });
        }),
      )
      .subscribe({
        next: (value) => {
          this.updateStatus(value.s3testsSvc, value.bench);
        },
      });
  }

  private updateStatus(
    s3tests: S3TestsStatusAPIResult,
    bench: BenchGetStatusAPIResult,
  ): void {
    this.updateS3Tests(s3tests);
    this.updateBench(bench);

    let busy = false;
    if (this.lastStatus.s3tests?.busy || this.lastStatus.bench?.busy) {
      busy = true;
    }
    this.busySubject.next(busy);
  }

  private updateS3Tests(res: S3TestsStatusAPIResult): void {
    const date = new Date(res.date);
    let status: S3TestsStatus;
    if (!res.busy) {
      status = { busy: false, lastRefreshed: date };
    } else {
      console.assert(!!res.current);
      const curr = res.current!;
      let progress: S3TestsProgress | undefined = undefined;
      if (!!curr.progress) {
        const total = curr.progress.tests_total;
        const done = curr.progress.tests_run;
        const percent =
          Math.round(((done * 100) / total + Number.EPSILON) * 100) / 100;
        progress = { total: total, done: done, percent: percent };
      }
      status = {
        busy: true,
        lastRefreshed: date,
        item: curr,
        progress: progress,
      };
    }
    const lastStatus = this.lastStatus.s3tests;
    if (!!lastStatus && lastStatus.busy == status.busy) {
      if (!status.busy) {
        // don't update subject if there's nothing to change.
        return;
      }
      if (!lastStatus.progress && !status.progress) {
        // no change in progress, don't update.
        return;
      } else if (
        !!lastStatus.progress &&
        !!status.progress &&
        lastStatus.progress.percent === status.progress.percent
      ) {
        return;
      }
    }
    this.lastStatus.s3tests = status;
    this.s3testsSubject.next(status);
  }

  private updateBench(res: BenchGetStatusAPIResult): void {
    const status: BenchStatus = {
      running: res.running,
      busy: res.busy,
      item: res.current,
    };
    const lastStatus: BenchStatus = this.lastStatus.bench;
    if (
      !!lastStatus &&
      lastStatus.running === status.running &&
      lastStatus.busy == status.busy
    ) {
      return;
    }
    this.lastStatus.bench = status;
    this.benchSubject.next(status);
  }

  public get s3tests(): BehaviorSubject<S3TestsStatus> {
    return this.s3testsSubject;
  }

  public get bench(): BehaviorSubject<BenchStatus> {
    return this.benchSubject;
  }

  public get busy(): BehaviorSubject<boolean> {
    return this.busySubject;
  }
}
