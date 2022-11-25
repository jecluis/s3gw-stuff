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
import { Component, Input, OnInit } from "@angular/core";
import { dump, JSON_SCHEMA } from "js-yaml";
import { finalize, Subscription } from "rxjs";
import { S3TestsAPIService } from "~/app/shared/services/api/s3tests-api.service";
import {
  S3TestsConfig,
  S3TestsConfigEntry,
} from "~/app/shared/types/s3tests.type";

@Component({
  selector: "s3gw-config-view",
  templateUrl: "./config-view.component.html",
  styleUrls: ["./config-view.component.scss"],
})
export class ConfigViewComponent implements OnInit {
  @Input()
  public config?: S3TestsConfigEntry;
  @Input()
  public busy: boolean = false;

  public yamlConfig: string = "";
  public isPreparingToRun: boolean = false;
  public failedToRun: boolean = false;

  private configSpec?: S3TestsConfig;
  private runSubscription?: Subscription;

  public constructor(private svc: S3TestsAPIService) {}

  public ngOnInit(): void {
    if (!!this.config) {
      this.configSpec = this.config.desc.config;
      this.yamlConfig = dump(this.configSpec, {
        noRefs: true,
        schema: JSON_SCHEMA,
        noCompatMode: true,
        forceQuotes: true,
        quotingType: '"',
      });
    }
  }

  public runConfig(): void {
    if (this.busy) {
      return;
    }

    this.failedToRun = false;
    this.isPreparingToRun = true;
    this.runSubscription = this.svc
      .runConfig(this.config!.uuid)
      .pipe(
        finalize(() => {
          this.isPreparingToRun = false;
        }),
      )
      .subscribe((res: boolean) => {
        if (!res) {
          this.failedToRun = true;
        }
        this.runSubscription!.unsubscribe();
      });
  }
}
