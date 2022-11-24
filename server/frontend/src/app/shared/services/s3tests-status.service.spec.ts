import { TestBed } from "@angular/core/testing";

import { S3TestsStatusService } from "./s3tests-status.service";

describe("S3TestsStatusService", () => {
  let service: S3TestsStatusService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(S3TestsStatusService);
  });

  it("should be created", () => {
    expect(service).toBeTruthy();
  });
});
