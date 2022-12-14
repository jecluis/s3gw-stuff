import { NgModule } from "@angular/core";
import { RouterModule, Routes } from "@angular/router";
import { S3testsComponent } from "~/app/pages/s3tests/s3tests.component";
import { BenchmarkComponent } from "~/app/pages/benchmark/benchmark.component";
import { ContainersComponent } from "~/app/pages/containers/containers.component";

const routes: Routes = [
  { path: "", redirectTo: "s3tests", pathMatch: "full" },
  { path: "s3tests", component: S3testsComponent },
  { path: "containers", component: ContainersComponent },
  { path: "bench", component: BenchmarkComponent },
];

@NgModule({
  imports: [RouterModule.forRoot(routes, { useHash: true })],
  exports: [RouterModule],
})
export class AppRoutingModule {}
