import { ComponentFixture, TestBed } from "@angular/core/testing";

import { ConfigResultsPlotComponent } from "./config-results-plot.component";

describe("ConfigResultsPlotComponent", () => {
  let component: ConfigResultsPlotComponent;
  let fixture: ComponentFixture<ConfigResultsPlotComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ConfigResultsPlotComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(ConfigResultsPlotComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });
});
