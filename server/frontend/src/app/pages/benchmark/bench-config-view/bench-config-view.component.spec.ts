import { ComponentFixture, TestBed } from "@angular/core/testing";

import { BenchConfigViewComponent } from "./bench-config-view.component";

describe("BenchConfigViewComponent", () => {
  let component: BenchConfigViewComponent;
  let fixture: ComponentFixture<BenchConfigViewComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [BenchConfigViewComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(BenchConfigViewComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });
});
