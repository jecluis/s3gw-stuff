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
  animate,
  state,
  style,
  transition,
  trigger,
} from "@angular/animations";
import { Component, Input, OnInit } from "@angular/core";
import { catchError, EMPTY, finalize, Subscription, take } from "rxjs";
import {
  S3TestsAPIService,
  S3TestsErrorEntry,
} from "~/app/shared/services/api/s3tests-api.service";

@Component({
  selector: "s3gw-s3tests-results-error-view",
  templateUrl: "./s3tests-results-error-view.component.html",
  styleUrls: ["./s3tests-results-error-view.component.scss"],
  animations: [
    trigger("collapseArrow", [
      state("closed", style({ transform: "rotate(0)" })),
      state("open", style({ transform: "rotate(90deg)" })),
      transition("* => *", [animate("100ms")]),
    ]),
  ],
})
export class S3TestsResultsErrorViewComponent implements OnInit {
  @Input()
  public uuid!: string;
  @Input()
  public name!: string;

  public expandedTrace: boolean = false;
  public expandedLog: boolean = false;
  public isFetching: boolean = false;
  public errorFetching: boolean = false;
  public hasResults: boolean = false;
  public traceText: string = "";
  public logText: string = "";

  private hasFetched: boolean = false;
  private fetchSubscription?: Subscription;

  public constructor(private svc: S3TestsAPIService) {}

  public ngOnInit(): void {
    return;
  }

  public toggleTrace(): void {
    this.expandedTrace = !this.expandedTrace;
    if (!this.expandedTrace) {
      return;
    }
    this.fetchIfNeeded();
  }

  public toggleLog(): void {
    this.expandedLog = !this.expandedLog;
    if (!this.expandedLog) {
      return;
    }
    this.fetchIfNeeded();
  }

  private fetchIfNeeded(): void {
    if (this.hasFetched) {
      return;
    }

    this.isFetching = true;
    this.fetchSubscription = this.svc
      .getErrors(this.uuid, this.name)
      .pipe(
        catchError((err) => {
          this.errorFetching = true;
          return EMPTY;
        }),
        finalize(() => {
          this.fetchSubscription?.unsubscribe();
          this.isFetching = false;
          this.hasFetched = true;
        }),
        take(1),
      )
      .subscribe((res: S3TestsErrorEntry) => {
        this.traceText = res.trace.join("\n");
        this.logText = res.log.join("\n");
        this.hasResults = true;
      });
  }
}
