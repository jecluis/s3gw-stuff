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
import { ServerAPIService } from "~/app/shared/services/api/server-api.service";
import {
  S3TestsConfigDesc,
  S3TestsConfigEntry,
  S3TestsConfigItem,
} from "~/app/shared/types/s3tests.type";

type S3TestsConfigTableEntry = {
  config: S3TestsConfigEntry;
  totalUnits: number;
  runnableUnits: number;
  collapsed: boolean;
};

type S3TestsConfigAPIResult = {
  date: Date;
  entries: S3TestsConfigItem[];
};

type S3TestsConfigPostResult = {
  date: string;
  uuid: string;
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

  // private configReloadInterval = 2000;
  private configSubscription?: Subscription;
  // private configRefreshTimerSubscription?: Subscription;

  public constructor(private svc: ServerAPIService) {}

  public ngOnInit(): void {
    this.reloadConfig();
  }

  public ngOnDestroy(): void {
    this.configSubscription?.unsubscribe();
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
