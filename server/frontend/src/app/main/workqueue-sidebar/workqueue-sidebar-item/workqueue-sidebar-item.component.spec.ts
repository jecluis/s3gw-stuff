import { ComponentFixture, TestBed } from "@angular/core/testing";

import { WorkQueueSidebarItemComponent } from "./workqueue-sidebar-item.component";

describe("WorkQueueSidebarItemComponent", () => {
  let component: WorkQueueSidebarItemComponent;
  let fixture: ComponentFixture<WorkQueueSidebarItemComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [WorkQueueSidebarItemComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(WorkQueueSidebarItemComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });
});
