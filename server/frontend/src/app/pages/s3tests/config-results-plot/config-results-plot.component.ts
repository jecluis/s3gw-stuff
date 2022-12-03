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
import { DatePipe } from "@angular/common";
import { Component, Input, OnInit } from "@angular/core";
import { catchError, EMPTY, finalize, take } from "rxjs";
import {
  S3TestsAPIService,
  S3TestsConfigResult,
} from "~/app/shared/services/api/s3tests-api.service";
import { S3TestsConfigEntry } from "~/app/shared/types/s3tests.type";

@Component({
  selector: "s3gw-config-results-plot",
  templateUrl: "./config-results-plot.component.html",
  styleUrls: ["./config-results-plot.component.scss"],
})
export class ConfigResultsPlotComponent implements OnInit {
  @Input()
  public config!: S3TestsConfigEntry;

  public hasData: boolean = false;
  public obtaining: boolean = false;
  public errorObtainingData: boolean = false;
  public data: Plotly.Data[] = [];

  public constructor(private svc: S3TestsAPIService) {}

  public ngOnInit(): void {
    this.plotResults();
  }

  private plotResults(): void {
    if (this.hasData) {
      return;
    }
    this.obtaining = true;
    this.svc
      .getConfigResults(this.config.uuid)
      .pipe(
        take(1),
        catchError((err) => {
          this.hasData = false;
          console.error(
            `error obtaining plot data for ${this.config.uuid}: `,
            err,
          );
          return EMPTY;
        }),
        finalize(() => {
          this.obtaining = false;
        }),
      )
      .subscribe((res: S3TestsConfigResult[]) => {
        if (res.length == 0) {
          console.debug(`No data to plot for config ${this.config.uuid}`);
          return;
        }
        this.processPlotData(res);
        this.hasData = true;
      });
  }

  private processPlotData(res: S3TestsConfigResult[]): void {
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

    this.data = [passedTrace, failedTrace, errorTrace];
  }
}
