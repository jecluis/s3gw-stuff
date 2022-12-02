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
import { S3TestsResultEntry } from "~/app/shared/types/s3tests.type";

type TestEntry = {
  name: string;
  status: string;
  isError: boolean;
  statusType: string;
  collapsed: boolean;
};

@Component({
  selector: "s3gw-s3tests-results-list",
  templateUrl: "./s3tests-results-list.component.html",
  styleUrls: ["./s3tests-results-list.component.scss"],
})
export class S3TestsResultsListComponent implements OnInit {
  @Input()
  public entry!: S3TestsResultEntry;

  public tests: { [name: string]: TestEntry } = {};
  public uuid!: string;
  public selected: string = "all";
  public total: number = 0;
  public passed: number = 0;
  public failed: number = 0;

  public constructor() {}

  public ngOnInit(): void {
    this.uuid = this.entry.uuid;

    Object.keys(this.entry.results).forEach((name: string) => {
      const res = this.entry.results[name];
      const isError = res !== "ok";
      ++this.total;
      if (isError) {
        ++this.failed;
      } else {
        ++this.passed;
      }

      this.tests[name] = {
        name: name,
        status: res,
        isError: isError,
        statusType: isError ? "error" : "ok",
        collapsed: true,
      };
    });
    return;
  }
}
