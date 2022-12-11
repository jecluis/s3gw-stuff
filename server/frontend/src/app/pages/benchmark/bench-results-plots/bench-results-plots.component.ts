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
import { finalize } from "rxjs";
import {
  BenchAPIService,
  Histogram,
  ResultHistograms,
} from "~/app/shared/services/api/bench-api.service";

type HistogramEntry = {
  data: Plotly.Data[];
  layout: Partial<Plotly.Layout>;
};

type HistogramPerOp = { [id: string]: HistogramEntry };

type HistogramPerTarget = { [id: string]: HistogramPerOp };

@Component({
  selector: "s3gw-bench-results-plots",
  templateUrl: "./bench-results-plots.component.html",
  styleUrls: ["./bench-results-plots.component.scss"],
})
export class BenchResultsPlotsComponent implements OnInit {
  @Input()
  public uuid!: string;

  public hasResults: boolean = false;
  public isFetching: boolean = false;
  public targets: string[] = [];
  public histograms: HistogramPerTarget = {};
  public hasSelected: boolean = false;
  public selectedTarget: string = "";
  public selectedOp: string = "";
  public selectedData?: Plotly.Data[];
  public selectedLayout?: Partial<Plotly.Layout>;

  public constructor(private svc: BenchAPIService) {}

  public ngOnInit(): void {
    this.isFetching = true;
    const sub = this.svc
      .getResultsHistograms(this.uuid)
      .pipe(
        finalize(() => {
          this.isFetching = false;
          sub.unsubscribe();
        }),
      )
      .subscribe((res: ResultHistograms) => {
        Object.keys(res).forEach((target: string) => {
          this.targets.push(target);
          Object.keys(res[target]).forEach((opname: string) => {
            if (!(target in this.histograms)) {
              this.histograms[target] = {};
            }
            const entry: HistogramEntry = {
              data: this.getData(res, target, opname),
              layout: this.getLayout(target, opname),
            };
            this.histograms[target][opname] = entry;
            if (!this.hasSelected) {
              this.selectedTarget = target;
              this.selectedOp = opname;
              this.selectedData = entry.data;
              this.selectedLayout = entry.layout;
              this.hasSelected = true;
            }
          });
        });
        this.hasResults = true;
      });
  }

  public selectOp(opname: string): void {
    if (!this.hasSelected) {
      return;
    }
    const ops = this.histograms[this.selectedTarget];
    if (!(opname in ops)) {
      return;
    }
    this.selectedOp = opname;
    this.selectedData = ops[opname].data;
    this.selectedLayout = ops[opname].layout;
  }

  public selectTarget(target: string): void {
    if (!this.hasSelected) {
      return;
    }
    if (!(target in this.histograms)) {
      return;
    }
    if (target === this.selectedTarget) {
      return;
    }
    const ops = Object.keys(this.histograms[target]);
    if (ops.length == 0) {
      return;
    }
    this.selectedOp = ops[0];
    this.selectedTarget = target;
    const entry = this.histograms[this.selectedTarget][this.selectedOp];
    this.selectedData = entry.data;
    this.selectedLayout = entry.layout;
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
      name: op,
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
}
