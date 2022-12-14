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
import { NgModule } from "@angular/core";
import { BrowserAnimationsModule } from "@angular/platform-browser/animations";
import { CommonModule } from "@angular/common";
import { S3testsComponent } from "~/app/pages/s3tests/s3tests.component";
import { ConfigViewComponent } from "~/app/pages/s3tests/config-view/config-view.component";
import { NgbCollapseModule } from "@ng-bootstrap/ng-bootstrap";
import { ReactiveFormsModule } from "@angular/forms";
import { S3TestsConfigComponent } from "~/app/pages/s3tests/s3tests-config/s3tests-config.component";
import { S3TestsResultsComponent } from "~/app/pages/s3tests/s3tests-results/s3tests-results.component";
import { S3TestsResultsListComponent } from "~/app/pages/s3tests/s3tests-results-list/s3tests-results-list.component";
import { S3TestsResultsErrorViewComponent } from "~/app/pages/s3tests/s3tests-results-error-view/s3tests-results-error-view.component";
import { AppRoutingModule } from "../app-routing.module";
import { ContainersComponent } from "~/app/pages/containers/containers.component";
import { SharedModule } from "~/app/shared/shared.module";
import { ConfigResultsPlotComponent } from "~/app/pages/s3tests/config-results-plot/config-results-plot.component";
import { BenchmarkComponent } from "~/app/pages/benchmark/benchmark.component";
import { BenchConfigComponent } from "~/app/pages/benchmark/bench-config/bench-config.component";
import { BenchResultsComponent } from "~/app/pages/benchmark/bench-results/bench-results.component";
import { BenchConfigViewComponent } from "~/app/pages/benchmark/bench-config-view/bench-config-view.component";
import { BenchResultsPlotsComponent } from "~/app/pages/benchmark/bench-results-plots/bench-results-plots.component";

@NgModule({
  declarations: [
    S3testsComponent,
    ConfigViewComponent,
    S3TestsConfigComponent,
    S3TestsResultsComponent,
    S3TestsResultsListComponent,
    S3TestsResultsErrorViewComponent,
    ContainersComponent,
    ConfigResultsPlotComponent,
    BenchmarkComponent,
    BenchConfigComponent,
    BenchResultsComponent,
    BenchConfigViewComponent,
    BenchResultsPlotsComponent,
  ],
  imports: [
    CommonModule,
    AppRoutingModule,
    BrowserAnimationsModule,
    NgbCollapseModule,
    ReactiveFormsModule,
    SharedModule,
  ],
  exports: [],
})
export class PagesModule {}
