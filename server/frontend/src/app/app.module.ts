import { NgModule } from "@angular/core";
import { BrowserModule } from "@angular/platform-browser";
import { HttpClientModule } from "@angular/common/http";

import { AppRoutingModule } from "~/app/app-routing.module";
import { AppComponent } from "~/app/app.component";
import { PagesModule } from "~/app/pages/pages.module";
import { SharedModule } from "~/app/shared/shared.module";
import { MainComponent } from "./main/main.component";

@NgModule({
  declarations: [AppComponent, MainComponent],
  imports: [
    BrowserModule,
    AppRoutingModule,
    HttpClientModule,
    PagesModule,
    SharedModule,
  ],
  providers: [],
  bootstrap: [AppComponent],
})
export class AppModule {}
