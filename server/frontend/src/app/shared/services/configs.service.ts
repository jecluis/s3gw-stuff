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
  map,
  Subscription,
  take,
  timer,
} from "rxjs";
import { S3TestsConfigItem } from "../types/s3tests.type";
import { BenchAPIService, BenchConfigEntry } from "./api/bench-api.service";
import {
  S3TestsAPIService,
  S3TestsConfigAPIResult,
} from "./api/s3tests-api.service";

enum ConfigType {
  s3tests = 1,
  bench = 2,
}

type ConfigEntry = {
  uuid: string;
  type: ConfigType;
  config: S3TestsConfigItem | BenchConfigEntry;
};

@Injectable({
  providedIn: "root",
})
export class ConfigsService implements OnDestroy {
  private refreshInterval: number = 1000;
  private refreshIntervalBackoff: number = 1000;
  private s3testsSubscription?: Subscription;
  private benchSubscription?: Subscription;
  private s3testsRefreshTimerSubscription?: Subscription;
  private benchRefreshTimerSubscription?: Subscription;

  private entryByUUID: { [id: string]: ConfigEntry } = {};
  private s3testsEntries: ConfigEntry[] = [];
  private benchEntries: ConfigEntry[] = [];

  private s3testsSubject: BehaviorSubject<S3TestsConfigItem[]> =
    new BehaviorSubject<S3TestsConfigItem[]>([]);
  private benchSubject: BehaviorSubject<BenchConfigEntry[]> =
    new BehaviorSubject<BenchConfigEntry[]>([]);

  public constructor(
    private s3testsSvc: S3TestsAPIService,
    private benchSvc: BenchAPIService,
  ) {
    this.refreshBench();
    this.refreshS3Tests();
  }

  public ngOnDestroy(): void {
    this.s3testsSubscription?.unsubscribe();
    this.s3testsRefreshTimerSubscription?.unsubscribe();
    this.benchSubscription?.unsubscribe();
    this.benchRefreshTimerSubscription?.unsubscribe();
  }

  public get s3tests(): BehaviorSubject<S3TestsConfigItem[]> {
    return this.s3testsSubject;
  }

  public get bench(): BehaviorSubject<BenchConfigEntry[]> {
    return this.benchSubject;
  }

  private getTimerInterval(): number {
    const backoff = Math.floor(Math.random() * this.refreshIntervalBackoff);
    return this.refreshInterval + backoff;
  }

  private refreshS3Tests(): void {
    this.s3testsSubscription = this.s3testsSvc
      .getConfig()
      .pipe(
        catchError((err) => {
          console.error("error obtaining s3tests configurations.");
          return EMPTY;
        }),
        take(1),
        finalize(() => {
          this.s3testsRefreshTimerSubscription = timer(this.getTimerInterval())
            .pipe(take(1))
            .subscribe(() => {
              this.s3testsSubscription!.unsubscribe();
              this.refreshS3Tests();
            });
        }),
        map((res: S3TestsConfigAPIResult) => res.entries),
      )
      .subscribe((res: S3TestsConfigItem[]) => {
        const uuids: string[] = [];
        let added: boolean = false;
        res.forEach((entry: S3TestsConfigItem) => {
          const uuid = entry.config.uuid;
          uuids.push(uuid);
          if (uuid in this.entryByUUID) {
            return;
          }
          const newEntry: ConfigEntry = {
            config: entry,
            type: ConfigType.s3tests,
            uuid: uuid,
          };
          this.entryByUUID[uuid] = newEntry;
          added = true;
        });
        this.updateConfigs(uuids, added, ConfigType.s3tests);
      });
  }

  private refreshBench(): void {
    this.benchSubscription = this.benchSvc
      .getConfig()
      .pipe(
        catchError((err) => {
          console.error("error obtaining benchmark configurations.");
          return EMPTY;
        }),
        take(1),
        finalize(() => {
          this.benchRefreshTimerSubscription = timer(this.getTimerInterval())
            .pipe(take(1))
            .subscribe(() => {
              this.benchSubscription!.unsubscribe();
              this.refreshBench();
            });
        }),
      )
      .subscribe((res: BenchConfigEntry[]) => {
        const uuids: string[] = [];
        let added: boolean = false;
        res.forEach((entry: BenchConfigEntry) => {
          const uuid = entry.uuid;
          uuids.push(uuid);
          if (uuid in this.entryByUUID) {
            return;
          }
          const newEntry: ConfigEntry = {
            config: entry,
            type: ConfigType.bench,
            uuid: uuid,
          };
          this.entryByUUID[uuid] = newEntry;
          added = true;
        });
        this.updateConfigs(uuids, added, ConfigType.bench);
      });
  }

  private cleanupEntries(existingUUIDs: string[], type: ConfigType): boolean {
    let deleted: boolean = false;
    Object.keys(this.entryByUUID).forEach((uuid: string) => {
      if (existingUUIDs.includes(uuid)) {
        return;
      } else if (this.entryByUUID[uuid].type !== type) {
        return;
      }
      delete this.entryByUUID[uuid];
      deleted = true;
    });
    return deleted;
  }

  private updateConfigs(
    existingUUIDs: string[],
    added: boolean,
    type: ConfigType,
  ): void {
    const deleted = this.cleanupEntries(existingUUIDs, type);
    if (!deleted && !added) {
      return;
    }
    const entries = Object.values(this.entryByUUID).filter(
      (value: ConfigEntry) => value.type === type,
    );
    if (type === ConfigType.bench) {
      this.benchEntries = entries;
      this.benchSubject.next(
        this.benchEntries.map((value) => <BenchConfigEntry>value.config),
      );
    } else if (type === ConfigType.s3tests) {
      this.s3testsEntries = entries;
      this.s3testsSubject.next(
        this.s3testsEntries.map((value) => <S3TestsConfigItem>value.config),
      );
    } else {
      console.error("unknown config type? ", type);
      return;
    }
  }
}
