import { ComponentFixture, TestBed } from "@angular/core/testing";

import { BenchResultsPlotsComponent } from "./bench-results-plots.component";

describe("BenchResultsPlotsComponent", () => {
  let component: BenchResultsPlotsComponent;
  let fixture: ComponentFixture<BenchResultsPlotsComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [BenchResultsPlotsComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(BenchResultsPlotsComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });
});
