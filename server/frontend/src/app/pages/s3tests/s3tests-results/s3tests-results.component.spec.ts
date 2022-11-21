import { ComponentFixture, TestBed } from "@angular/core/testing";

import { S3TestsResultsComponent } from "./s3tests-results.component";

describe("S3TestsResultsComponent", () => {
  let component: S3TestsResultsComponent;
  let fixture: ComponentFixture<S3TestsResultsComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [S3TestsResultsComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(S3TestsResultsComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });
});
