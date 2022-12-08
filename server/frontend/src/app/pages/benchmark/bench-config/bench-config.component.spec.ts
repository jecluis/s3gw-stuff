import { ComponentFixture, TestBed } from "@angular/core/testing";

import { BenchConfigComponent } from "./bench-config.component";

describe("BenchConfigComponent", () => {
  let component: BenchConfigComponent;
  let fixture: ComponentFixture<BenchConfigComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [BenchConfigComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(BenchConfigComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });
});
