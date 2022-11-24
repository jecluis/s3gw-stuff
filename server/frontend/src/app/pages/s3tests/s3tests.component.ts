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
import {
  S3TestsProgress,
  S3TestsStatus,
  S3TestsStatusService,
} from "~/app/shared/services/s3tests-status.service";
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
  public currentProgress?: S3TestsProgress;
  public currentDuration?: number;

  private statusUpdateInterval = 1000;
  private statusSubscription?: Subscription;
  private statusRefreshTimerSubscription?: Subscription;

  public constructor(private svc: S3TestsStatusService) {}

  public ngOnInit(): void {
    this.refreshStatus();
  }

  public ngOnDestroy(): void {
    this.statusSubscription?.unsubscribe();
    this.statusRefreshTimerSubscription?.unsubscribe();
  }

  private refreshStatus(): void {
    this.statusSubscription = this.svc.status.subscribe({
      next: (status: S3TestsStatus) => {
        if (!status) {
          return;
        }
        this.isBusy = status.busy;
        this.currentConfig = status.item?.config;
        this.currentProgress = status.progress;
      },
    });

    return;
  }
}
