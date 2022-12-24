import { ComponentFixture, TestBed } from "@angular/core/testing";

import { WorkQueueSidebarComponent } from "./workqueue-sidebar.component";

describe("WorkQueueSidebarComponent", () => {
  let component: WorkQueueSidebarComponent;
  let fixture: ComponentFixture<WorkQueueSidebarComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [WorkQueueSidebarComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(WorkQueueSidebarComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });
});
