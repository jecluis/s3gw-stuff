import { NgModule } from "@angular/core";
import { BrowserAnimationsModule } from "@angular/platform-browser/animations";
import { CommonModule } from "@angular/common";
import { S3testsComponent } from "~/app/pages/s3tests/s3tests.component";
import { ConfigViewComponent } from "~/app/pages/s3tests/config-view/config-view.component";
import { NgbCollapseModule } from "@ng-bootstrap/ng-bootstrap";
import { ReactiveFormsModule } from "@angular/forms";
import { S3TestsConfigComponent } from "~/app/pages/s3tests/s3tests-config/s3tests-config.component";
import { S3TestsResultsComponent } from "~/app/pages/s3tests/s3tests-results/s3tests-results.component";

@NgModule({
  declarations: [
    S3testsComponent,
    ConfigViewComponent,
    S3TestsConfigComponent,
    S3TestsResultsComponent,
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
