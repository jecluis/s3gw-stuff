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
  BenchRunDesc,
  BenchTargetProgress,
} from "~/app/shared/services/api/bench-api.service";
import {
  BenchStatus,
  StatusService,
} from "~/app/shared/services/status.service";

type Progress = {
  target: string;
  progress: number;
  targetNum: number;
  totalTargets: number;
  duration: number;
  state: string;
};

@Component({
  selector: "s3gw-benchmark",
  templateUrl: "./benchmark.component.html",
  styleUrls: ["./benchmark.component.scss"],
})
export class BenchmarkComponent implements OnInit, OnDestroy {
  public isBusy: boolean = false;
  public isBenchBusy: boolean = false;
  public isBenchAvailable: boolean = false;
  public currentRun?: BenchRunDesc;
  public currentProgress?: Progress;

  private busySubscription?: Subscription;
  private statusSubscription?: Subscription;

  public constructor(private statusSvc: StatusService) {}

  public ngOnInit(): void {
    this.busySubscription = this.statusSvc.busy.subscribe({
      next: (v: boolean) => {
        this.isBusy = v;
      },
    });
    this.statusSubscription = this.statusSvc.bench.subscribe({
      next: (s: BenchStatus) => {
        if (!s) {
          return;
        }
        this.isBenchBusy = s.busy;
        this.isBenchAvailable = s.running;
        this.currentRun = s.item;
        if (!this.isBenchBusy) {
          return;
        }
        console.assert(!!this.currentRun);
        console.assert(!!this.currentRun!.progress);
        const p = this.currentRun!.progress;
        let doneTargets: number = 0;
        let currTarget: BenchTargetProgress | undefined = undefined;
        p.targets.forEach((target: BenchTargetProgress) => {
          if (target.is_done) {
            doneTargets++;
          } else if (target.is_running) {
            currTarget = target;
          } else {
            console.error("unknown target state: ", target);
          }
        });
        console.assert(!!currTarget);
        console.assert(!!currTarget);
        let state: string = "unknown";
        if (currTarget!.state === 0) {
          state = "starting";
        } else if (currTarget!.state === 1) {
          state = "preparing";
        } else if (currTarget!.state === 2) {
          state = "running";
        }
        console.log("current target: ", currTarget);
        this.currentProgress = {
          duration: p.duration,
          target: currTarget!.name,
          targetNum: doneTargets + 1,
          totalTargets: p.targets.length,
          progress: currTarget!.value,
          state: state,
        };
      },
    });
  }

  public ngOnDestroy(): void {
    this.busySubscription?.unsubscribe();
    this.statusSubscription?.unsubscribe();
  }
}
