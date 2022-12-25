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
import { Component, OnInit } from "@angular/core";
import { catchError, EMPTY, finalize, take } from "rxjs";
import { refreshRotateAnimation } from "~/app/shared/animations";
import {
  BenchAPIService,
  BenchResult,
  BenchResultMap,
  BenchTargetProgress,
} from "~/app/shared/services/api/bench-api.service";

type TableEntry = {
  date: Date;
  config: string;
  uuid: string;
  targets: string[];
  duration: number;
  collapsed: boolean;
};

@Component({
  selector: "s3gw-bench-results",
  templateUrl: "./bench-results.component.html",
  styleUrls: ["./bench-results.component.scss"],
  animations: [refreshRotateAnimation],
})
export class BenchResultsComponent implements OnInit {
  public refreshRotateState: number = 0;
  public entries: TableEntry[] = [];
  public isLoading = false;
  public isErrorOnLoading = false;
  public firstLoadComplete = false;

  public constructor(private svc: BenchAPIService) {}

  public ngOnInit(): void {
    this.reload();
  }

  public refresh(): void {
    this.refreshRotateState++;
    this.reload();
  }

  private reload(): void {
    this.isLoading = true;
    const sub = this.svc
      .getResults()
      .pipe(
        catchError((err) => {
          console.error("Error obtaining bench results.");
          this.isErrorOnLoading = true;
          return EMPTY;
        }),
        finalize(() => {
          this.isLoading = false;
          sub.unsubscribe();
        }),
        take(1),
      )
      .subscribe((res: BenchResultMap) => {
        const lst: TableEntry[] = [];
        Object.values(res).forEach((value: BenchResult) => {
          const targets = value.progress.progress.targets.map(
            (target: BenchTargetProgress) => target.name,
          );
          lst.push({
            date: new Date(value.progress.time_start!),
            config: value.config.name,
            uuid: value.uuid,
            targets: targets,
            duration: value.progress.duration,
            collapsed: true,
          });
        });
        this.entries = lst.sort((a, b) => b.date.getTime() - a.date.getTime());
      });
  }

  public toggleEntry(entry: TableEntry): void {
    entry.collapsed = !entry.collapsed;
    if (entry.collapsed) {
      return;
    }
  }
}
