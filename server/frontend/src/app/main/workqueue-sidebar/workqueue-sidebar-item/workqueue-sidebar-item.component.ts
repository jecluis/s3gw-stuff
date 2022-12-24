import {
  Component,
  Input,
  OnChanges,
  OnInit,
  SimpleChanges,
} from "@angular/core";
import {
  WorkQueueEntry,
  WorkQueueEntryKind,
} from "~/app/shared/services/workqueue.service";

@Component({
  selector: "s3gw-workqueue-sidebar-item",
  templateUrl: "./workqueue-sidebar-item.component.html",
  styleUrls: ["./workqueue-sidebar-item.component.scss"],
})
export class WorkQueueSidebarItemComponent implements OnInit, OnChanges {
  @Input()
  public item!: WorkQueueEntry;
  public kind: string = "unknown";
  public duration: string = "forever";

  public constructor() {}

  public ngOnInit(): void {
    switch (this.item.kind) {
      case WorkQueueEntryKind.Bench:
        this.kind = "Benchmark";
        break;
      case WorkQueueEntryKind.S3Tests:
        this.kind = "S3Tests";
        break;
    }
    this.handleDuration();
  }

  public ngOnChanges(changes: SimpleChanges): void {
    this.handleDuration();
  }

  private handleDuration(): void {
    if (this.item.duration === 0) {
      this.duration = "-";
      return;
    }

    this.duration = `${this.item.duration} seconds`;
  }
}
