import { ComponentFixture, TestBed } from "@angular/core/testing";

import { S3TestsResultsListComponent } from "./s3tests-results-list.component";

describe("S3TestsResultsListComponent", () => {
  let component: S3TestsResultsListComponent;
  let fixture: ComponentFixture<S3TestsResultsListComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [S3TestsResultsListComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(S3TestsResultsListComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });
});
