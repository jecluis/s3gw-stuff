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
import { Component, Input, OnDestroy, OnInit } from "@angular/core";
import { dump, JSON_SCHEMA } from "js-yaml";
import { catchError, EMPTY, finalize, Subscription } from "rxjs";
import {
  BenchAPIService,
  BenchConfigEntry,
} from "~/app/shared/services/api/bench-api.service";

@Component({
  selector: "s3gw-bench-config-view",
  templateUrl: "./bench-config-view.component.html",
  styleUrls: ["./bench-config-view.component.scss"],
})
export class BenchConfigViewComponent implements OnInit, OnDestroy {
  @Input()
  public config!: BenchConfigEntry;

  public yamlConfig: string = "";
  public failedToRun: boolean = false;
  public isPreparingToRun: boolean = false;

  private runSubscription?: Subscription;

  public constructor(private benchSvc: BenchAPIService) {}

  public ngOnInit(): void {
    console.assert(!!this.config);
    this.yamlConfig = dump(this.config.config, {
      noRefs: true,
      schema: JSON_SCHEMA,
      noCompatMode: true,
      forceQuotes: true,
      quotingType: '"',
    });
  }

  public ngOnDestroy(): void {
    this.runSubscription?.unsubscribe();
  }

  public runConfig(): void {
    console.debug("run config: ", this.config.uuid);

    this.failedToRun = false;
    this.isPreparingToRun = true;

    this.runSubscription = this.benchSvc
      .runConfig(this.config.uuid)
      .pipe(
        catchError(() => {
          this.failedToRun = true;
          return EMPTY;
        }),
        finalize(() => {
          this.isPreparingToRun = false;
          this.runSubscription!.unsubscribe();
          this.runSubscription = undefined;
        }),
      )
      .subscribe((uuid: string) => {
        this.failedToRun = false;
      });
  }
}
