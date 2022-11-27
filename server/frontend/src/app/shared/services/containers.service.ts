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
import { Injectable, OnDestroy } from "@angular/core";
import {
  BehaviorSubject,
  catchError,
  EMPTY,
  finalize,
  Subscription,
  take,
  timer,
} from "rxjs";
import { ServerAPIService } from "./api/server-api.service";

export type ContainerEntry = {
  command: string[];
  created: string;
  started: string;
  running: boolean;
  state: string;
  id: string;
  image_id: string;
  image_name: {
    name: string;
    tag: string;
  };
  names: string[];
};

type ContainersPSAPIResult = {
  date: string;
  result: ContainerEntry[];
};

@Injectable({
  providedIn: "root",
})
export class ContainersService implements OnDestroy {
  private listSubject: BehaviorSubject<ContainerEntry[]> = new BehaviorSubject<
    ContainerEntry[]
  >([]);

  private refreshInterval: number = 1000;
  private refreshSubscription?: Subscription;
  private refreshTimerSubscription?: Subscription;

  public constructor(private api: ServerAPIService) {
    this.refresh();
  }

  public ngOnDestroy(): void {
    this.refreshTimerSubscription?.unsubscribe();
    this.refreshSubscription?.unsubscribe();
  }

  private refresh(): void {
    this.refreshSubscription = this.api
      .get<ContainersPSAPIResult>("/containers/ps")
      .pipe(
        catchError((err) => {
          console.error("error refreshing containers: ", err);
          return EMPTY;
        }),
        finalize(() => {
          this.refreshTimerSubscription = timer(this.refreshInterval)
            .pipe(take(1))
            .subscribe(() => {
              this.refreshSubscription!.unsubscribe();
              this.refresh();
            });
        }),
        take(1),
      )
      .subscribe((res: ContainersPSAPIResult) => {
        this.listSubject.next(res.result);
      });
  }

  public get containers(): BehaviorSubject<ContainerEntry[]> {
    return this.listSubject;
  }
}
