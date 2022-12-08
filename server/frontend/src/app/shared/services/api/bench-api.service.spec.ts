import { TestBed } from "@angular/core/testing";

import { BenchAPIService } from "./bench-api.service";

describe("BenchAPIService", () => {
  let service: BenchAPIService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(BenchAPIService);
  });

  it("should be created", () => {
    expect(service).toBeTruthy();
  });
});
