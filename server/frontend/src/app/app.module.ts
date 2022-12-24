import { NgModule } from "@angular/core";
import { BrowserModule } from "@angular/platform-browser";
import { HttpClientModule } from "@angular/common/http";

import { AppRoutingModule } from "~/app/app-routing.module";
import { AppComponent } from "~/app/app.component";
import { PagesModule } from "~/app/pages/pages.module";
import { SharedModule } from "~/app/shared/shared.module";
import { MainComponent } from "~/app/main/main.component";
import { NgbOffcanvasModule } from "@ng-bootstrap/ng-bootstrap";
import { WorkQueueSidebarComponent } from "~/app/main/workqueue-sidebar/workqueue-sidebar.component";
import { WorkQueueSidebarItemComponent } from "~/app/main/workqueue-sidebar/workqueue-sidebar-item/workqueue-sidebar-item.component";

@NgModule({
  declarations: [
    AppComponent,
    MainComponent,
    WorkQueueSidebarComponent,
    WorkQueueSidebarItemComponent,
  ],
  imports: [
    BrowserModule,
    AppRoutingModule,
    HttpClientModule,
    PagesModule,
    SharedModule,
    NgbOffcanvasModule,
  ],
  providers: [],
  bootstrap: [AppComponent],
})
export class AppModule {}
