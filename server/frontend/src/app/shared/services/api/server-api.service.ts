/*
 * Copyright 2022 SUSE, LLC
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
import { HttpClient, HttpParams } from "@angular/common/http";
import { Injectable } from "@angular/core";
import { Observable } from "rxjs";

export type ServerAPIOptions = {
  body?: any;
  params?: HttpParams | { [param: string]: string | number | boolean };
};

@Injectable({
  providedIn: "root",
})
export class ServerAPIService {
  public url = "/api";

  constructor(private http: HttpClient) {}

  public get<T>(endpoint: string): Observable<T> {
    return this.http.get<T>(this.buildURL(endpoint));
  }

  public post<T>(endpoint: string, options?: ServerAPIOptions): Observable<T> {
    return this.http.post<T>(this.buildURL(endpoint), options?.body, {
      params: options?.params,
    });
  }

  private buildURL(endpoint: string): string {
    if (endpoint.startsWith("/")) {
      return `${this.url}${endpoint}`;
    }
    return `${this.url}/${endpoint}`;
  }
}
