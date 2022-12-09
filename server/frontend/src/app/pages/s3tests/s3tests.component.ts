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
import { Subscription } from "rxjs";
import {
  S3TestsProgress,
  S3TestsStatus,
  StatusService,
} from "~/app/shared/services/status.service";
import { S3TestsConfigEntry } from "~/app/shared/types/s3tests.type";

@Component({
  selector: "s3gw-s3tests",
  templateUrl: "./s3tests.component.html",
  styleUrls: ["./s3tests.component.scss"],
})
export class S3testsComponent implements OnInit, OnDestroy {
  public isBusy: boolean = false;
  public isS3TestsBusy: boolean = false;
  public currentConfig?: S3TestsConfigEntry;
  public currentProgress?: S3TestsProgress;
  public currentDuration?: number;

  private busySubscription?: Subscription;
  private statusSubscription?: Subscription;

  public constructor(private status: StatusService) {}

  public ngOnInit(): void {
    this.statusSubscription = this.status.s3tests.subscribe({
      next: (status: S3TestsStatus) => {
        if (!status) {
          return;
        }
        this.isS3TestsBusy = status.busy;
        this.currentConfig = status.item?.config;
        this.currentProgress = status.progress;
      },
    });
    this.busySubscription = this.status.busy.subscribe({
      next: (busy: boolean) => {
        this.isBusy = busy;
      },
    });
  }

  public ngOnDestroy(): void {
    this.statusSubscription?.unsubscribe();
    this.busySubscription?.unsubscribe();
  }
}
