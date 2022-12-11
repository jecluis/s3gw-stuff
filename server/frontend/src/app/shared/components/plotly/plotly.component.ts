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
import {
  Component,
  ElementRef,
  Input,
  OnChanges,
  OnInit,
  SimpleChanges,
  ViewChild,
} from "@angular/core";
import * as Plotly from "plotly.js-dist-min";

@Component({
  selector: "s3gw-plotly",
  templateUrl: "./plotly.component.html",
  styleUrls: ["./plotly.component.scss"],
})
export class PlotlyComponent implements OnInit, OnChanges {
  @ViewChild("plot", { static: true })
  public plotElement!: ElementRef;

  @Input()
  public data: Plotly.Data[] = [];
  @Input()
  public layout?: Partial<Plotly.Layout>;

  public constructor() {}

  public ngOnInit(): void {
    this.create().then(() => {});
  }

  public ngOnChanges(changes: SimpleChanges): void {
    if ("data" in changes || "layout" in changes) {
      this.create().then(() => {});
    }
  }

  private create(): Promise<Plotly.PlotlyHTMLElement> {
    return Plotly.newPlot(
      this.plotElement.nativeElement,
      this.data,
      this.layout,
    );
  }
}
