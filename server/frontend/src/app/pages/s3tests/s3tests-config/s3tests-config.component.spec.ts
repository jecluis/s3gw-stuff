import { ComponentFixture, TestBed } from "@angular/core/testing";

import { S3TestsConfigComponent } from "~/app/pages/s3tests/s3tests-config/s3tests-config.component";

describe("S3TestsConfigComponent", () => {
  let component: S3TestsConfigComponent;
  let fixture: ComponentFixture<S3TestsConfigComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [S3TestsConfigComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(S3TestsConfigComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });
});
