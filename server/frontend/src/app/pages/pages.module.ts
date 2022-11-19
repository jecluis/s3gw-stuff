import { NgModule } from "@angular/core";
import { BrowserAnimationsModule } from "@angular/platform-browser/animations";
import { CommonModule } from "@angular/common";
import { S3testsComponent } from "~/app/pages/s3tests/s3tests.component";
import { ConfigViewComponent } from "~/app/pages/s3tests/config-view/config-view.component";


@NgModule({
  declarations: [
    S3testsComponent,
    ConfigViewComponent
  ],
  imports: [
    CommonModule,
    BrowserAnimationsModule,
  ],
  exports: [
    S3testsComponent
  ]
})
export class PagesModule { }
