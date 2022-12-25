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
import { Event, NavigationEnd, Router } from "@angular/router";
import { Subscription } from "rxjs";
import {
  BenchConfigEntry,
  BenchProgress,
  BenchTargetProgress,
} from "~/app/shared/services/api/bench-api.service";
import {
  S3TestsProgress,
  WorkQueueEntry,
  WorkQueueEntryKind,
  WorkQueueProgress,
  WorkQueueService,
  WorkQueueStatus,
  WorkQueueStatusEntry,
} from "~/app/shared/services/workqueue.service";
import { S3TestsConfigEntry } from "~/app/shared/types/s3tests.type";

@Component({
  selector: "s3gw-status-bar",
  templateUrl: "./status-bar.component.html",
  styleUrls: ["./status-bar.component.scss"],
})
export class StatusBarComponent implements OnInit, OnDestroy {
  public currentRoute: string = "";
  public isBusy: boolean = false;
  public currentRunning?: WorkQueueStatusEntry;
  public details?: {
    kind: string;
    name: string;
    isBench: boolean;
    isS3Tests: boolean;
  };
  public benchProgress?: {
    duration: string;
    target: string;
    targetNum: number;
    totalTargets: number;
    progress: number;
    state: string;
  };
  public s3testsProgress?: {
    duration: string;
    done: number;
    total: number;
    progress: number;
  };

  private routerSubscription?: Subscription;
  private statusSubscription?: Subscription;

  public constructor(private router: Router, private wqSvc: WorkQueueService) {}

  public ngOnInit(): void {
    this.routerSubscription = this.router.events.subscribe((event: Event) => {
      if (event instanceof NavigationEnd) {
        switch (event.urlAfterRedirects) {
          case "/s3tests":
            this.currentRoute = "s3tests";
            break;
          case "/bench":
            this.currentRoute = "benchmark";
            break;
          case "/containers":
            this.currentRoute = "containers";
            break;
          default:
            this.currentRoute = "unknown";
            break;
        }
      }
    });

    this.statusSubscription = this.wqSvc.status.subscribe({
      next: (status: WorkQueueStatus) => {
        if (status.current != this.currentRunning) {
          console.debug("new workqueue status: ", status);
          this.handleStatusUpdate(status);
        }
      },
    });
  }

  public ngOnDestroy(): void {
    this.routerSubscription?.unsubscribe();
    this.statusSubscription?.unsubscribe();
  }

  private handleStatusUpdate(status: WorkQueueStatus): void {
    this.isBusy = status.is_running;
    this.currentRunning = status.current;

    if (!this.currentRunning) {
      return;
    }

    if (status.current!.item.kind === WorkQueueEntryKind.Bench) {
      this.handleBenchStatusUpdate(
        status.current!.item,
        status.current!.config as BenchConfigEntry,
        status.current!.progress,
      );
    } else if (status.current!.item.kind === WorkQueueEntryKind.S3Tests) {
      this.handleS3TestsStatusUpdate(
        status.current!.item,
        status.current!.config as S3TestsConfigEntry,
        status.current!.progress,
      );
    }
  }

  private handleBenchStatusUpdate(
    item: WorkQueueEntry,
    config: BenchConfigEntry,
    progress: WorkQueueProgress,
  ) {
    this.details = {
      kind: "benchmark",
      name: config.config.name,
      isBench: true,
      isS3Tests: false,
    };

    const benchProgress: BenchProgress = progress.progress as BenchProgress;
    let doneTargets: number = 0;
    let currTarget: BenchTargetProgress | undefined;
    benchProgress.targets.forEach((target: BenchTargetProgress) => {
      if (target.is_done) {
        ++doneTargets;
      } else if (target.is_running) {
        currTarget = target;
      }
    });

    let targetName: string = "preparing target";
    let targetProgress: number = 0;
    let stateStr: string = "~?~";

    if (benchProgress.targets.length > 0 && !!currTarget) {
      targetName = currTarget.name;
      targetProgress = currTarget.value;

      switch (currTarget.state) {
        case 0:
          stateStr = "starting";
          break;
        case 1:
          stateStr = "preparing";
          break;
        case 2:
          stateStr = "running";
          break;
      }
    }

    this.benchProgress = {
      duration: this.durationToStr(progress.duration),
      target: targetName,
      targetNum: doneTargets + 1,
      totalTargets: benchProgress.targets.length,
      progress: targetProgress,
      state: stateStr,
    };
  }

  private handleS3TestsStatusUpdate(
    item: WorkQueueEntry,
    config: S3TestsConfigEntry,
    progress: WorkQueueProgress,
  ) {
    this.details = {
      kind: "s3tests",
      name: config.desc.name,
      isBench: false,
      isS3Tests: true,
    };

    const s3testsProgress = progress.progress as S3TestsProgress;
    const done = s3testsProgress.tests_run;
    const total = s3testsProgress.tests_total;
    const percent =
      Math.round(((done * 100) / total + Number.EPSILON) * 100) / 100;
    this.s3testsProgress = {
      duration: this.durationToStr(progress.duration),
      done: done,
      total: total,
      progress: percent,
    };
  }

  private durationToStr(value: number): string {
    return `${value} seconds`;
  }
}
