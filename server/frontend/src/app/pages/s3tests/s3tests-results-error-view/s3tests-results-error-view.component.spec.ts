import { ComponentFixture, TestBed } from "@angular/core/testing";

import { S3TestsResultsErrorViewComponent } from "./s3tests-results-error-view.component";

describe("S3TestsResultsErrorViewComponent", () => {
  let component: S3TestsResultsErrorViewComponent;
  let fixture: ComponentFixture<S3TestsResultsErrorViewComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [S3TestsResultsErrorViewComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(S3TestsResultsErrorViewComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });
});
