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
import {
  catchError,
  EMPTY,
  finalize,
  Observable,
  Subscription,
  take,
} from "rxjs";
import {
  S3TestsAPIService,
  S3TestsResultsAPIResult,
} from "~/app/shared/services/api/s3tests-api.service";
import { S3TestsResultEntry } from "~/app/shared/types/s3tests.type";

type S3TestsResultsTableEntry = {
  result: S3TestsResultEntry;
  uuid: string;
  config_name: string;
  date: Date;
  duration: number;
  status: string;
  collapsed: boolean;
};

@Component({
  selector: "s3gw-s3tests-results",
  templateUrl: "./s3tests-results.component.html",
  styleUrls: ["./s3tests-results.component.scss"],
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
export class S3TestsResultsComponent implements OnInit, OnDestroy {
  public firstResultsLoadComplete: boolean = false;
  public loadingResults: boolean = false;
  public errorOnLoadingResults: boolean = false;
  public resultsList: S3TestsResultsTableEntry[] = [];
  public resultsListLastUpdated?: Date;
  public refreshResultsRotateState: number = 0;
  public resultsSubscription?: Subscription;

  public constructor(private svc: S3TestsAPIService) {}

  public ngOnInit(): void {
    this.reloadResults();
  }

  public ngOnDestroy(): void {
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
            date: tstart,
            duration: duration,
            status: success ? "ok" : "error",
            collapsed: true,
          });
        });
        this.resultsList = lst.sort(
          (a, b) => b.date.getTime() - a.date.getTime(),
        );
      });
  }

  private loadResults(): Observable<S3TestsResultsAPIResult> {
    return this.svc.getResults();
  }

  public refreshResults(): void {
    this.refreshResultsRotateState += 1;
    if (!this.loadingResults) {
      this.reloadResults();
    }
  }
}
