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
import { catchError, EMPTY, finalize, take } from "rxjs";
import { refreshRotateAnimation } from "~/app/shared/animations";
import {
  BenchAPIService,
  BenchResult,
  BenchResultMap,
  BenchTargetProgress,
  Histogram,
  ResultHistograms,
} from "~/app/shared/services/api/bench-api.service";

type HistogramEntry = {
  data: Plotly.Data[];
  layout: Partial<Plotly.Layout>;
};

type ResultsEntry = {
  hasResults: boolean;
  fetching: boolean;
  results: ResultHistograms;
};

type TableEntry = {
  date: Date;
  config: string;
  uuid: string;
  targets: string[];
  duration: number;
  collapsed: boolean;
  results: ResultsEntry;
  histograms: { [id: string]: { [id: string]: HistogramEntry } };
};

@Component({
  selector: "s3gw-bench-results",
  templateUrl: "./bench-results.component.html",
  styleUrls: ["./bench-results.component.scss"],
  animations: [refreshRotateAnimation],
})
export class BenchResultsComponent implements OnInit {
  public refreshRotateState: number = 0;
  public entries: TableEntry[] = [];
  public isLoading = false;
  public isErrorOnLoading = false;
  public firstLoadComplete = false;

  public constructor(private svc: BenchAPIService) {}

  public ngOnInit(): void {
    this.reload();
  }

  public refresh(): void {
    this.refreshRotateState++;
    this.reload();
  }

  private reload(): void {
    this.isLoading = true;
    const sub = this.svc
      .getResults()
      .pipe(
        catchError((err) => {
          console.error("Error obtaining bench results.");
          this.isErrorOnLoading = true;
          return EMPTY;
        }),
        finalize(() => {
          this.isLoading = false;
          sub.unsubscribe();
        }),
        take(1),
      )
      .subscribe((res: BenchResultMap) => {
        const lst: TableEntry[] = [];
        Object.values(res).forEach((value: BenchResult) => {
          const targets = value.progress.targets.map(
            (target: BenchTargetProgress) => target.name,
          );
          lst.push({
            date: new Date(value.progress.time_start!),
            config: value.config.name,
            uuid: value.uuid,
            targets: targets,
            duration: value.progress.duration,
            collapsed: true,
            results: { hasResults: false, fetching: false, results: {} },
            histograms: {},
          });
        });
        this.entries = lst.sort((a, b) => b.date.getTime() - a.date.getTime());
      });
  }

  public toggleEntry(entry: TableEntry): void {
    entry.collapsed = !entry.collapsed;
    if (entry.collapsed) {
      return;
    }
    if (!entry.results.hasResults) {
      this.fetchResults(entry);
    }
  }

  private getData(
    results: ResultHistograms,
    target: string,
    op: string,
  ): Plotly.Data[] {
    const hist: Histogram = results[target][op];
    const trace: Plotly.Data = {
      type: "histogram",
      x: hist.data,
      title: { text: `Latency distribution for ${target}'s ${op}` },
      name: op,
      xaxis: "milliseconds",
      yaxis: "count",
      showlegend: true,
    };
    return [trace];
  }

  private getLayout(target: string, op: string): Partial<Plotly.Layout> {
    return {
      title: `Latency distribution for ${target}'s ${op}`,
      xaxis: { title: "milliseconds" },
      yaxis: { title: "count" },
    };
  }

  private fetchResults(entry: TableEntry): void {
    if (entry.results.fetching) {
      return;
    }
    entry.results.fetching = true;
    const sub = this.svc
      .getResultsHistograms(entry.uuid)
      .pipe(
        finalize(() => {
          entry.results.fetching = false;
        }),
      )
      .subscribe((res: ResultHistograms) => {
        console.log(`histograms for ${entry.uuid}:`, res);
        entry.results.hasResults = true;
        entry.results.results = res;
        Object.keys(res).forEach((target: string) => {
          Object.keys(res[target]).forEach((opname: string) => {
            if (!(target in entry.histograms)) {
              entry.histograms[target] = {};
            }
            entry.histograms[target][opname] = {
              data: this.getData(res, target, opname),
              layout: this.getLayout(target, opname),
            };
          });
        });
      });
  }
}
