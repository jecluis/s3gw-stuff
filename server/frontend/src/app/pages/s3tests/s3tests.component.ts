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
  AbstractControl,
  FormControl,
  FormGroup,
  ValidationErrors,
  ValidatorFn,
  Validators,
} from "@angular/forms";
import { dump, load, JSON_SCHEMA } from "js-yaml";
import { config } from "process";
import { catchError, EMPTY, finalize, Observable, take } from "rxjs";
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

export type S3TestsCollectedUnits = {
  all: string[];
  filtered: string[];
};

export type S3TestsConfigItem = {
  config: S3TestsConfigEntry;
  tests: S3TestsCollectedUnits;
};

type S3TestsConfigAPIResult = {
  date: Date;
  entries: S3TestsConfigItem[];
};

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

type S3TestsConfigTableEntry = {
  config: S3TestsConfigEntry;
  totalUnits: number;
  runnableUnits: number;
  collapsed: boolean;
};

type S3TestsResultsTableEntry = {
  result: S3TestsResultEntry;
  uuid: string;
  config_name: string;
  duration: number;
  status: string;
  collapsed: boolean;
};

type S3TestsConfigPostResult = {
  date: string;
  uuid: string;
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
  public firstConfigLoadComplete: boolean = false;
  public loadingConfig: boolean = false;
  public errorOnLoadingConfig: boolean = false;
  public configList: S3TestsConfigTableEntry[] = [];
  public configListLastUpdated?: Date;
  public refreshRotateState: number = 0;
  public isNewConfigCollapsed: boolean = true;
  public newConfigButtonLabel: string = "New";
  public newConfigForm = new FormGroup({
    configName: new FormControl("", [
      Validators.required,
      this.configNameValidator(),
    ]),
    configContents: new FormControl("", [
      Validators.required,
      this.configContentsValidator(),
    ]),
  });
  public errorOnConfigSubmit: boolean = false;
  public submittingConfig: boolean = false;

  private defaultConfigContents = {
    container: {
      image: "ghcr.io/aquarist-labs/s3gw:latest",
      ports: ["7480:7480"],
      volumes: [],
    },
    tests: {
      suite: "s3tests_boto3.functional",
      ignore: [],
      exclude: [],
      include: [],
    },
  };

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

  constructor(private svc: ServerAPIService) {}

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
        take(1),
      )
      .subscribe((cfg: S3TestsConfigAPIResult) => {
        this.errorOnLoadingConfig = false;
        let lst: S3TestsConfigTableEntry[] = [];
        cfg.entries.forEach((e: S3TestsConfigItem) => {
          lst.push({
            config: e.config,
            totalUnits: e.tests.all.length,
            runnableUnits: e.tests.filtered.length,
            collapsed: true,
          });
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

  public toggleNewConfig(): void {
    this.isNewConfigCollapsed = !this.isNewConfigCollapsed;
    this.newConfigButtonLabel = this.isNewConfigCollapsed ? "New" : "Cancel";

    if (this.isNewConfigCollapsed) {
      this.newConfigForm.reset();
    } else {
      let yaml = dump(this.defaultConfigContents, {
        noRefs: true,
        schema: JSON_SCHEMA,
        noCompatMode: true,
        forceQuotes: true,
        quotingType: '"',
      });
      this.newConfigForm.setValue({ configName: "", configContents: yaml });
    }
  }

  public createNewConfig(): void {
    if (this.isNewConfigCollapsed || !!this.newConfigForm.errors) {
      return;
    }

    if (!this.configContents.value || !this.configName.value) {
      return;
    }

    if (this.submittingConfig) {
      return;
    }

    let config: any | null = null;
    try {
      config = load(this.configContents.value, { schema: JSON_SCHEMA });
    } catch (e) {
      console.error("Invalid yaml provided!");
      return;
    }
    const desc: S3TestsConfigDesc = {
      name: this.configName.value,
      config: config,
    };

    this.submittingConfig = true;
    this.svc
      .post<S3TestsConfigPostResult>("/s3tests/config", desc)
      .pipe(
        catchError((err) => {
          console.error("error submitting new config: ", err);
          this.errorOnConfigSubmit = true;
          return EMPTY;
        }),
        finalize(() => {
          this.submittingConfig = false;
        }),
        take(1),
      )
      .subscribe((res: S3TestsConfigPostResult) => {
        this.toggleNewConfig();
        this.refreshConfig();
      });
  }

  private configNameExists(name: string): boolean {
    let valid = this.configList.every(
      (entry: S3TestsConfigTableEntry) => entry.config.desc.name !== name,
    );
    return !valid;
  }

  private isValidYAML(value: string): boolean {
    try {
      load(value, {
        schema: JSON_SCHEMA,
      });
    } catch (e) {
      return false;
    }
    return true;
  }

  private configNameValidator(): ValidatorFn {
    return (control: AbstractControl): ValidationErrors | null => {
      const value: string = control.value;
      return this.configNameExists(value)
        ? { nameExists: { value: value } }
        : null;
    };
  }

  private configContentsValidator(): ValidatorFn {
    return (control: AbstractControl): ValidationErrors | null => {
      const value: string = control.value;
      if (!this.isValidYAML(value)) {
        return { invalidContents: { value: value } };
      }
      return null;
    };
  }

  public get newForm() {
    return this.newConfigForm.controls;
  }
  public get configName() {
    return this.newForm.configName;
  }
  public get configContents() {
    return this.newForm.configContents;
  }
}
