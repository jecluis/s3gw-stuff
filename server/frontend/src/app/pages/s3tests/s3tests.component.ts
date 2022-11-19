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

type S3TestsTableEntry = {
  config: S3TestsConfigEntry;
  collapsed: boolean;
};

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
  public configList: S3TestsTableEntry[] = [];
  public configListLastUpdated?: Date;
  public refreshRotateState: number = 0;

  private configReloadInterval = 2000;
  private configSubscription?: Subscription;
  private configRefreshTimerSubscription?: Subscription;

  constructor(private svc: ServerAPIService) { }

  ngOnInit(): void {
    this.reloadConfig();
  }

  ngOnDestroy(): void {
    this.configSubscription?.unsubscribe();
    this.configRefreshTimerSubscription?.unsubscribe();
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
        let lst: S3TestsTableEntry[] = [];
        cfg.config.forEach((e: S3TestsConfigEntry) => {
          lst.push({config: e, collapsed: false});
        })
        this.configList = lst;
        this.configListLastUpdated = cfg.date;
        console.log("reload @ ", cfg.date);
      });
  }

  private loadConfig(): Observable<S3TestsConfigAPIResult> {
    return this.svc.get<S3TestsConfigAPIResult>("/s3tests/config");
  }

  public refreshConfig(): void {
    console.log("refresh");
    this.refreshRotateState += 1;
    if (!this.loadingConfig) {
      console.log("reloading...");
      this.reloadConfig();
    }
  }

}
