import { ComponentFixture, TestBed } from "@angular/core/testing";

import { S3testsComponent } from "./s3tests.component";

describe("S3testsComponent", () => {
  let component: S3testsComponent;
  let fixture: ComponentFixture<S3testsComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ S3testsComponent ]
    })
    .compileComponents();

    fixture = TestBed.createComponent(S3testsComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });
});
