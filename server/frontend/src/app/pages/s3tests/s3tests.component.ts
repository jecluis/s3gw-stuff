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
import { animate, style, transition, trigger } from "@angular/animations";
import { Component, OnDestroy, OnInit } from "@angular/core";
import { catchError, EMPTY, finalize, Observable, take } from "rxjs";
import { Subscription } from "rxjs";
import { ServerAPIService } from "~/app/shared/services/api/server-api.service";
import { S3TestsConfigEntry } from "~/app/shared/types/s3tests.type";

type S3TestsResultEntry = {
  uuid: string;
  time_start: string;
  time_end: string;
  config: S3TestsConfigEntry;
  results: { [id: string]: string };
  is_error: boolean;
  error_msg: string;
  progress?: {
    tests_total: number;
    tests_run: number;
  };
};

type S3TestsResultsAPIResult = {
  date: Date;
  results: { [id: string]: S3TestsResultEntry };
};

type S3TestsResultsTableEntry = {
  result: S3TestsResultEntry;
  uuid: string;
  config_name: string;
  duration: number;
  status: string;
  collapsed: boolean;
};

@Component({
  selector: "s3gw-s3tests",
  templateUrl: "./s3tests.component.html",
  styleUrls: ["./s3tests.component.scss"],
  animations: [
    trigger("refreshRotate", [
      transition("void => *", style({ transform: "rotate(0)" })),
      transition("* => *", [
        style({ transform: "rotate(0)" }),
        animate("1500ms ease-out", style({ transform: "rotate(360deg)" })),
      ]),
    ]),
  ],
})
export class S3testsComponent implements OnInit, OnDestroy {
  public firstResultsLoadComplete: boolean = false;
  public loadingResults: boolean = false;
  public errorOnLoadingResults: boolean = false;
  public resultsList: S3TestsResultsTableEntry[] = [];
  public resultsListLastUpdated?: Date;
  public refreshResultsRotateState: number = 0;
  public resultsSubscription?: Subscription;

  constructor(private svc: ServerAPIService) {}

  ngOnInit(): void {
    this.reloadResults();
  }

  ngOnDestroy(): void {
    this.resultsSubscription?.unsubscribe();
  }

  private reloadResults() {
    this.loadingResults = true;
    this.resultsSubscription = this.loadResults()
      .pipe(
        catchError((err) => {
          this.errorOnLoadingResults = true;
          return EMPTY;
        }),
        finalize(() => {
          this.loadingResults = false;
          this.firstResultsLoadComplete = true;
        }),
        take(1),
      )
      .subscribe((results: S3TestsResultsAPIResult) => {
        this.errorOnLoadingResults = false;
        this.resultsListLastUpdated = results.date;
        let lst: S3TestsResultsTableEntry[] = [];
        Object.keys(results.results).forEach((k: string) => {
          let res = results.results[k];
          let cfgName = res.config.desc.name;
          let tstart: Date = new Date(res.time_start);
          let tend: Date = new Date(res.time_end);
          let duration = tend.getTime() - tstart.getTime();
          let success = Object.values(res.results).every((r) => r === "ok");
          lst.push({
            result: res,
            uuid: res.uuid,
            config_name: cfgName,
            duration: duration,
            status: success ? "ok" : "error",
            collapsed: true,
          });
        });
        this.resultsList = lst;
      });
  }

  private loadResults(): Observable<S3TestsResultsAPIResult> {
    return this.svc.get<S3TestsResultsAPIResult>("/s3tests/results");
  }

  public refreshResults(): void {
    this.refreshResultsRotateState += 1;
    if (!this.loadingResults) {
      this.reloadResults();
    }
  }
}
