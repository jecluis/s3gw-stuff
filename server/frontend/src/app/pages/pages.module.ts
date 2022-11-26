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

@NgModule({
  declarations: [
    S3testsComponent,
    ConfigViewComponent,
    S3TestsConfigComponent,
    S3TestsResultsComponent,
    S3TestsResultsListComponent,
    S3TestsResultsErrorViewComponent,
  ],
  imports: [
    CommonModule,
    BrowserAnimationsModule,
    NgbCollapseModule,
    ReactiveFormsModule,
  ],
  exports: [S3testsComponent],
})
export class PagesModule {}
