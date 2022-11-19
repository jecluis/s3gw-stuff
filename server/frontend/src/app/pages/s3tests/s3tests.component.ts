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
import { animate, state, style, transition, trigger } from "@angular/animations";
import { Component, OnDestroy, OnInit } from "@angular/core";
import { catchError, EMPTY, finalize, Observable, take, timer } from "rxjs";
import { Subscription } from "rxjs";
import { ServerAPIService } from "~/app/shared/services/api/server-api.service";

export type S3TestsConfig = {
  container: {
    image: string;
    ports: string[];
    volumes: string[];
  };
  tests: {
    suite: string;
    ignore: string[];
    exclude: string[];
    include: string[];
  };
};

export type S3TestsConfigDesc = {
  name: string;
  config: S3TestsConfig;
};

export type S3TestsConfigEntry = {
  uuid: string;
  desc: S3TestsConfigDesc;
};

type S3TestsConfigAPIResult = {
  date: Date;
  config: S3TestsConfigEntry[];
};

type S3TestsResultEntry = {
  uuid: string;
  time_start: string;
  time_end: string;
  config: S3TestsConfigEntry;
  results: {[id: string]: string};
  is_error: boolean;
  error_msg: string;
  progress?: {
    tests_total: number;
    tests_run: number;
  };
};

type S3TestsResultsAPIResult = {
  date: Date;
  results: {[id: string]: S3TestsResultEntry};
};

type S3TestsConfigTableEntry = {
  config: S3TestsConfigEntry;
  collapsed: boolean;
};

type S3TestsResultsTableEntry = {
  result: S3TestsResultEntry;
  uuid: string;
  config_name: string;
  duration: number;
  status: string;
  collapsed: boolean;
}

@Component({
  selector: "s3gw-s3tests",
  templateUrl: "./s3tests.component.html",
  styleUrls: ["./s3tests.component.scss"],
  animations: [
    trigger("refreshRotate", [
      transition("void => *", style({transform: "rotate(0)"})),
      transition("* => *", [
        style({transform: "rotate(0)"}),
        animate("1500ms ease-out",
          style({transform: "rotate(360deg)"})
        )
      ])
    ])
  ]
})
export class S3testsComponent implements OnInit, OnDestroy {

  public firstConfigLoadComplete: boolean = false;
  public loadingConfig: boolean = false;
  public errorOnLoadingConfig: boolean = false;
  public configList: S3TestsConfigTableEntry[] = [];
  public configListLastUpdated?: Date;
  public refreshRotateState: number = 0;

  private configReloadInterval = 2000;
  private configSubscription?: Subscription;
  private configRefreshTimerSubscription?: Subscription;

  public firstResultsLoadComplete: boolean = false;
  public loadingResults: boolean = false;
  public errorOnLoadingResults: boolean = false;
  public resultsList: S3TestsResultsTableEntry[] = [];
  public resultsListLastUpdated?: Date;
  public refreshResultsRotateState: number = 0;
  public resultsSubscription?: Subscription;

  constructor(private svc: ServerAPIService) { }

  ngOnInit(): void {
    this.reloadConfig();
    this.reloadResults();
  }

  ngOnDestroy(): void {
    this.configSubscription?.unsubscribe();
    this.configRefreshTimerSubscription?.unsubscribe();
    this.resultsSubscription?.unsubscribe();
  }

  private reloadConfig() {
    this.loadingConfig = true;
    this.configSubscription = this.loadConfig()
      .pipe(
        catchError((err) => {
          this.errorOnLoadingConfig = true;
          return EMPTY;
        }),
        finalize(() => {
          this.loadingConfig = false;
          this.firstConfigLoadComplete = true;
          // this.configRefreshTimerSubscription = timer(this.configReloadInterval)
          //   .pipe(take(1))
          //   .subscribe(() => {
          //     this.configSubscription!.unsubscribe();
          //     this.reloadConfig();
          //   });
        }),
        take(1)
      )
      .subscribe((cfg: S3TestsConfigAPIResult) => {
        this.errorOnLoadingConfig = false;
        let lst: S3TestsConfigTableEntry[] = [];
        cfg.config.forEach((e: S3TestsConfigEntry) => {
          lst.push({config: e, collapsed: true});
        });
        this.configList = lst;
        this.configListLastUpdated = cfg.date;
        console.log("reload @ ", cfg.date);
      });
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
        take(1)
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
          let success = Object.values(res.results).every(r => r === "ok");
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

  private loadConfig(): Observable<S3TestsConfigAPIResult> {
    return this.svc.get<S3TestsConfigAPIResult>("/s3tests/config");
  }

  private loadResults(): Observable<S3TestsResultsAPIResult> {
    return this.svc.get<S3TestsResultsAPIResult>("/s3tests/results");
  }

  public refreshConfig(): void {
    console.log("refresh");
    this.refreshRotateState += 1;
    if (!this.loadingConfig) {
      console.log("reloading...");
      this.reloadConfig();
    }
  }

  public refreshResults(): void {
    this.refreshResultsRotateState += 1;
    if (!this.loadingResults) {
      this.reloadResults();
    }
  }

}
