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
import { dump, JSON_SCHEMA, load } from "js-yaml";
import {
  catchError,
  EMPTY,
  finalize,
  Observable,
  Subscription,
  take,
} from "rxjs";
import * as Plotly from "plotly.js-dist-min";
import {
  S3TestsAPIService,
  S3TestsConfigAPIPostResult,
  S3TestsConfigAPIResult,
  S3TestsConfigResult,
} from "~/app/shared/services/api/s3tests-api.service";
import {
  S3TestsStatus,
  S3TestsStatusService,
} from "~/app/shared/services/s3tests-status.service";
import {
  S3TestsConfigDesc,
  S3TestsConfigEntry,
  S3TestsConfigItem,
} from "~/app/shared/types/s3tests.type";
import { DatePipe } from "@angular/common";

type S3TestsConfigTableEntry = {
  config: S3TestsConfigEntry;
  totalUnits: number;
  runnableUnits: number;
  collapsed: boolean;
};

type PlotDataInfo = {
  hasPlotData: boolean;
  obtaining: boolean;
  data: Plotly.Data[];
};

@Component({
  selector: "s3gw-s3tests-config",
  templateUrl: "./s3tests-config.component.html",
  styleUrls: ["./s3tests-config.component.scss"],
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
export class S3TestsConfigComponent implements OnInit, OnDestroy {
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
  public isRunning: boolean = false;

  public plotDataByUUID: { [id: string]: PlotDataInfo } = {};

  public plotData: Plotly.Data[] = [
    {
      x: [1, 2, 3],
      y: [2, 6, 3],
      type: "scatter",
      mode: "lines+markers",
      marker: { color: "red" },
      name: "foo",
    },
    { x: [1, 2, 3], y: [2, 5, 3], type: "bar" },
  ];

  private defaultConfigContents = {
    container: {
      image: "ghcr.io/aquarist-labs/s3gw:latest",
      target_port: 7480,
    },
    tests: {
      suite: "s3tests_boto3.functional",
      ignore: [],
      exclude: [],
      include: [],
    },
  };

  private configSubscription?: Subscription;
  private statusSubscription?: Subscription;

  public constructor(
    private svc: S3TestsAPIService,
    private statusSvc: S3TestsStatusService,
  ) {}

  public ngOnInit(): void {
    this.reloadConfig();
    this.statusSubscription = this.statusSvc.status.subscribe({
      next: (s: S3TestsStatus) => {
        this.isRunning = !!s ? s.busy : false;
      },
    });
  }

  public ngOnDestroy(): void {
    this.configSubscription?.unsubscribe();
    this.statusSubscription?.unsubscribe();
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
        }),
        take(1),
      )
      .subscribe((cfg: S3TestsConfigAPIResult) => {
        this.errorOnLoadingConfig = false;
        let lst: S3TestsConfigTableEntry[] = [];
        const plotData: { [id: string]: PlotDataInfo } = {};
        cfg.entries.forEach((e: S3TestsConfigItem) => {
          lst.push({
            config: e.config,
            totalUnits: e.tests.all.length,
            runnableUnits: e.tests.filtered.length,
            collapsed: true,
          });
          plotData[e.config.uuid] = {
            hasPlotData: false,
            obtaining: false,
            data: [],
          };
        });
        this.plotDataByUUID = plotData;
        this.configList = lst;
        this.configListLastUpdated = cfg.date;
        console.log("reload @ ", cfg.date);
      });
  }

  private loadConfig(): Observable<S3TestsConfigAPIResult> {
    return this.svc.getConfig();
  }

  public refreshConfig(): void {
    console.log("refresh");
    this.refreshRotateState += 1;
    if (!this.loadingConfig) {
      console.log("reloading...");
      this.reloadConfig();
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
      .postConfig(desc)
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
      .subscribe((res: S3TestsConfigAPIPostResult) => {
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

  public toggleEntry(entry: S3TestsConfigTableEntry): void {
    entry.collapsed = !entry.collapsed;
    if (!entry.collapsed) {
      this.plotResults(entry.config.uuid);
    }
  }

  public plotResults(uuid: string): void {
    console.assert(uuid in this.plotDataByUUID);
    const info = this.plotDataByUUID[uuid];
    if (info.hasPlotData) {
      return;
    }
    info.obtaining = true;
    this.svc
      .getConfigResults(uuid)
      .pipe(
        take(1),
        catchError((err) => {
          info.hasPlotData = false;
          console.error(`error obtaining plot data for ${uuid}: `, err);
          return EMPTY;
        }),
        finalize(() => {
          info.obtaining = false;
        }),
      )
      .subscribe((res: S3TestsConfigResult[]) => {
        if (res.length == 0) {
          console.debug(`No data to plot for config ${uuid}`);
          return;
        }
        this.processPlotData(uuid, res);
        info.hasPlotData = true;
      });
  }

  private processPlotData(uuid: string, res: S3TestsConfigResult[]): void {
    console.assert(uuid in this.plotDataByUUID);
    const info = this.plotDataByUUID[uuid];

    const x: string[] = [];
    const error: number[] = [];
    const failed: number[] = [];
    const passed: number[] = [];

    const nByDate: { [id: string]: number } = {};
    const datepipe: DatePipe = new DatePipe("en-US");
    res.forEach((entry: S3TestsConfigResult) => {
      const date = new Date(entry.date);
      let datestr = datepipe.transform(date, "MMM d");
      if (!(datestr! in nByDate)) {
        nByDate[datestr!] = 0;
      }
      nByDate[datestr!]++;
      if (nByDate[datestr!] > 1) {
        datestr = `${datestr} (${nByDate[datestr!]})`;
      }
      x.push(datestr!);
      error.push(entry.error);
      failed.push(entry.failed);
      passed.push(entry.passed);
    });

    const errorTrace: Plotly.Data = {
      name: "error",
      marker: { color: "red" },
      type: "bar",
      x: x,
      y: error,
    };
    const failedTrace: Plotly.Data = {
      name: "failed",
      marker: { color: "orange" },
      type: "bar",
      x: x,
      y: failed,
    };
    const passedTrace: Plotly.Data = {
      name: "passed",
      marker: { color: "green" },
      type: "bar",
      x: x,
      y: passed,
    };

    info.data = [passedTrace, failedTrace, errorTrace];
    console.log("plot data: ", this.plotDataByUUID[uuid]);
  }
}
