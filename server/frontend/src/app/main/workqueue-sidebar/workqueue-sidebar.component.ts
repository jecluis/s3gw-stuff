import { Component, OnDestroy, OnInit } from "@angular/core";
import { finalize, Subscription, take, timer } from "rxjs";
import {
  WorkQueueEntry,
  WorkQueueService,
  WorkQueueStatus,
} from "~/app/shared/services/workqueue.service";

@Component({
  selector: "s3gw-workqueue-sidebar",
  templateUrl: "./workqueue-sidebar.component.html",
  styleUrls: ["./workqueue-sidebar.component.scss"],
})
export class WorkQueueSidebarComponent implements OnInit, OnDestroy {
  public constructor(private wqSvc: WorkQueueService) {}

  public hasAny: boolean = false;
  public hasCurrent: boolean = false;
  public current?: WorkQueueEntry;
  public waiting: WorkQueueEntry[] = [];

  private wqUpdateInterval = 1000;
  private wqRefreshSubscription?: Subscription;
  private wqSubscription?: Subscription;

  public ngOnInit(): void {
    this.refresh();
  }

  public ngOnDestroy(): void {
    this.wqSubscription?.unsubscribe();
    this.wqRefreshSubscription?.unsubscribe();
  }

  private refresh(): void {
    this.wqSubscription = this.wqSvc
      .getWorkQueue()
      .pipe(
        take(1),
        finalize(() => {
          this.wqRefreshSubscription = timer(this.wqUpdateInterval)
            .pipe(take(1))
            .subscribe(() => {
              this.wqSubscription!.unsubscribe();
              this.refresh();
            });
        }),
      )
      .subscribe((status: WorkQueueStatus) => {
        this.updateStatus(status);
      });
  }

  private updateStatus(status: WorkQueueStatus): void {
    this.current = status.current;
    this.waiting = status.waiting;
    this.hasCurrent = !!this.current;
    this.hasAny = this.hasCurrent || this.waiting.length > 0;
  }
}
