#!/bin/bash

if ! uvicorn --version >&/dev/null ; then
  echo "error: unable to find uvicorn" >/dev/stderr
  exit 1
fi

BENCH_DEBUG=1 uvicorn bench-server:app_factory --factory \
  --app-dir server/ \
  --host 0.0.0.0 --port 4880

