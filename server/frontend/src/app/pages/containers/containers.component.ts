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
import { Component, OnDestroy, OnInit } from "@angular/core";
import { Subscription } from "rxjs";
import {
  ContainerEntry,
  ContainersService,
} from "~/app/shared/services/containers.service";

@Component({
  selector: "s3gw-containers",
  templateUrl: "./containers.component.html",
  styleUrls: ["./containers.component.scss"],
})
export class ContainersComponent implements OnInit, OnDestroy {
  public running: ContainerEntry[] = [];
  public stopped: ContainerEntry[] = [];

  private containersSubscription?: Subscription;

  public constructor(private svc: ContainersService) {}

  public ngOnInit(): void {
    this.refresh();
  }

  public ngOnDestroy(): void {
    this.containersSubscription?.unsubscribe();
  }

  private refresh(): void {
    this.containersSubscription = this.svc.containers.subscribe({
      next: (entries: ContainerEntry[]) => {
        this.update(entries);
      },
    });
  }

  private update(entries: ContainerEntry[]): void {
    const running: ContainerEntry[] = [];
    const stopped: ContainerEntry[] = [];

    entries.forEach((entry: ContainerEntry) => {
      if (entry.running) {
        running.push(entry);
      } else {
        stopped.push(entry);
      }
    });

    this.running = running;
    this.stopped = stopped;
  }
}
