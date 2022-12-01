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
import { catchError, EMPTY, finalize, Subscription } from "rxjs";
import {
  ContainerEntry,
  ContainersService,
} from "~/app/shared/services/containers.service";

type EntryInfo = {
  hasLogs: boolean;
  obtainingLogs: boolean;
  errorObtainingLogs: boolean;
  isCollapsed: boolean;
};

type ContainerTableEntry = {
  id: string;
  name: string;
  image: string;
  state: string;
  command: string;
  startedAt: Date;
  createdAt: Date;
  isRunning: boolean;
  info: EntryInfo;
};

@Component({
  selector: "s3gw-containers",
  templateUrl: "./containers.component.html",
  styleUrls: ["./containers.component.scss"],
})
export class ContainersComponent implements OnInit, OnDestroy {
  public running: ContainerTableEntry[] = [];
  public stopped: ContainerTableEntry[] = [];

  public entryByID: { [id: string]: ContainerTableEntry } = {};
  public logs: { [id: string]: string } = {};

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
    const entriesByID: { [id: string]: ContainerEntry } = {};

    entries.forEach((entry: ContainerEntry) => {
      const tableEntry: ContainerTableEntry = {
        id: entry.id,
        name: entry.names[0],
        image: `${entry.image_name.name}:${entry.image_name.tag}`,
        state: entry.state,
        command: entry.command.join(),
        createdAt: new Date(entry.created),
        startedAt: new Date(entry.started),
        isRunning: entry.running,
        info: {
          errorObtainingLogs: false,
          hasLogs: false,
          obtainingLogs: false,
          isCollapsed: true,
        },
      };

      entriesByID[entry.id] = entry;
      if (entry.id in this.entryByID) {
        const existing = this.entryByID[entry.id];
        if (existing.state === entry.state) {
          return;
        }
      }
      this.entryByID[entry.id] = tableEntry;
    });

    Object.keys(this.entryByID).forEach((id: string) => {
      if (!(id in entriesByID)) {
        delete this.entryByID[id];
      }
    });

    const running: ContainerTableEntry[] = [];
    const stopped: ContainerTableEntry[] = [];
    Object.keys(this.entryByID).forEach((id: string) => {
      const entry = this.entryByID[id];
      if (entry.isRunning) {
        running.push(entry);
      } else {
        stopped.push(entry);
      }
    });

    this.running = running.sort(
      (a, b) => b.createdAt.getTime() - a.createdAt.getTime(),
    );
    this.stopped = stopped.sort(
      (a, b) => b.createdAt.getTime() - a.createdAt.getTime(),
    );
  }

  public toggleEntry(entry: ContainerTableEntry): void {
    const info = entry.info;
    info.isCollapsed = !info.isCollapsed;
    if (info.isCollapsed) {
      return;
    }

    if (!info.hasLogs && !info.obtainingLogs) {
      info.obtainingLogs = true;
      this.obtainLogs(entry);
    }
  }

  private obtainLogs(entry: ContainerTableEntry): void {
    const sub: Subscription = this.svc
      .getLogs(entry.id)
      .pipe(
        catchError((err) => {
          console.error(`error obtaining logs for ${entry.id}: `, err);
          entry.info.errorObtainingLogs = true;
          return EMPTY;
        }),
        finalize(() => {
          entry.info.obtainingLogs = false;
          sub.unsubscribe();
        }),
      )
      .subscribe((logs: string) => {
        entry.info.hasLogs = true;
        entry.info.errorObtainingLogs = false;
        this.logs[entry.id] = logs;
      });
  }
}
