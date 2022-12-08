import { ComponentFixture, TestBed } from "@angular/core/testing";

import { BenchResultsComponent } from "./bench-results.component";

describe("BenchResultsComponent", () => {
  let component: BenchResultsComponent;
  let fixture: ComponentFixture<BenchResultsComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [BenchResultsComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(BenchResultsComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });
});
