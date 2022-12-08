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
import {
  AbstractControl,
  FormControl,
  FormGroup,
  ValidationErrors,
  ValidatorFn,
  Validators,
} from "@angular/forms";
import { dump, JSON_SCHEMA, load } from "js-yaml";
import { catchError, EMPTY, finalize, take } from "rxjs";
import { refreshRotateAnimation } from "~/app/shared/animations";
import {
  BenchAPIService,
  BenchConfig,
  BenchConfigDesc,
  BenchConfigParams,
  BenchConfigTarget,
} from "~/app/shared/services/api/bench-api.service";

type TableEntry = {
  name: string;
  uuid: string;
  targets: string[];
  config: BenchConfig;
  collapsed: boolean;
};

@Component({
  selector: "s3gw-bench-config",
  templateUrl: "./bench-config.component.html",
  styleUrls: ["./bench-config.component.scss"],
  animations: [refreshRotateAnimation],
})
export class BenchConfigComponent implements OnInit {
  public refreshRotateState: number = 0;
  public entries: TableEntry[] = [];

  public newConfigButtonLabel: string = "New";
  public isNewConfigCollapsed: boolean = true;
  public isSubmittingConfig: boolean = false;
  public newConfigForm = new FormGroup({
    name: new FormControl("", [
      Validators.required,
      this.configNameValidator(),
    ]),
    contents: new FormControl("", [
      Validators.required,
      this.configContentsValidator(),
    ]),
  });

  private defaultConfig: { params: BenchConfigParams } & {
    targets: { [id: string]: BenchConfigTarget };
  } = {
    params: {
      num_objects: 1000,
      object_size: "1mb",
      duration: "5m",
    },
    targets: {
      minio: {
        image: "quay.io/minio/minio:latest",
        port: 9000,
        access_key: "minioadmin",
        secret_key: "minioadmin",
      },
      s3gw: {
        image: "ghcr.io/aquarist-labs/s3gw:latest",
        port: 7480,
        access_key: "test",
        secret_key: "test",
      },
    },
  };

  public constructor(private svc: BenchAPIService) {}

  public ngOnInit(): void {
    this.reload();
  }

  public refresh(): void {
    this.refreshRotateState++;
    this.reload();
  }

  private reload(): void {
    const sub = this.svc
      .getConfig()
      .pipe(
        take(1),
        finalize(() => {}),
      )
      .subscribe((res: BenchConfigDesc[]) => {
        const entries: TableEntry[] = [];
        res.forEach((desc: BenchConfigDesc) => {
          const targets = Object.keys(desc.config.targets);
          entries.push({
            name: desc.config.name,
            uuid: desc.uuid,
            targets: targets,
            config: desc.config,
            collapsed: true,
          });
        });
        this.entries = entries;
      });
  }

  public toggleEntry(entry: TableEntry): void {
    entry.collapsed = !entry.collapsed;
  }

  public toggleNewConfig(): void {
    this.isNewConfigCollapsed = !this.isNewConfigCollapsed;
    this.newConfigButtonLabel = this.isNewConfigCollapsed ? "New" : "Cancel";

    if (this.isNewConfigCollapsed) {
      this.newConfigForm.reset();
    } else {
      const yaml = dump(this.defaultConfig, {
        noRefs: true,
        schema: JSON_SCHEMA,
        noCompatMode: true,
        forceQuotes: true,
        quotingType: '"',
      });
      this.newConfigForm.setValue({ name: "", contents: yaml });
    }
  }

  public createNewConfig(): void {
    if (this.isNewConfigCollapsed || !!this.newConfigForm.errors) {
      return;
    }

    if (!this.configContents.value || !this.configName.value) {
      return;
    }

    if (this.isSubmittingConfig) {
      return;
    }

    let config: any | null = null;
    try {
      config = load(this.configContents.value, { schema: JSON_SCHEMA });
    } catch (e) {
      console.error("Invalid YAML provided!");
      return;
    }
    if (!("targets" in config) || !("params" in config)) {
      console.error("Invalid config provided!");
      return;
    }
    const desc: BenchConfig = {
      name: this.configName.value,
      params: config.params,
      targets: config.targets,
    };

    this.isSubmittingConfig = true;
    const sub = this.svc
      .postConfig(desc)
      .pipe(
        take(1),
        catchError((err) => {
          console.error("error submitting bench config: ", err);
          return EMPTY;
        }),
        finalize(() => {
          this.isSubmittingConfig = false;
          sub.unsubscribe();
        }),
      )
      .subscribe((uuid: string) => {
        this.toggleNewConfig();
        this.reload();
      });
  }

  private configNameExists(name: string): boolean {
    if (!!name && name.length == 0) {
      return false;
    }
    const valid = this.entries.every(
      (entry: TableEntry) => entry.name !== name,
    );
    return !valid;
  }

  private isValidYAML(value: string): boolean {
    try {
      load(value, { schema: JSON_SCHEMA });
    } catch (e) {
      return false;
    }
    return true;
  }

  private configNameValidator(): ValidatorFn {
    return (control: AbstractControl): ValidationErrors | null => {
      const value: string = control.value;
      return this.configNameExists(value)
        ? { nameExists: { value: true } }
        : null;
    };
  }

  private configContentsValidator(): ValidatorFn {
    return (control: AbstractControl): ValidationErrors | null => {
      const value: string = control.value;
      if (!this.isValidYAML(value)) {
        return { invalidContents: { value: true } };
      }
      return null;
    };
  }

  public get configName() {
    return this.newConfigForm.controls.name;
  }

  public get configContents() {
    return this.newConfigForm.controls.contents;
  }
}
