import { TestBed } from "@angular/core/testing";

import { S3TestsAPIService } from "./s3tests-api.service";

describe("S3TestsAPIService", () => {
  let service: S3TestsAPIService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(S3TestsAPIService);
  });

  it("should be created", () => {
    expect(service).toBeTruthy();
  });
});
