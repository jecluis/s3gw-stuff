# Copyright (C) 2022 SUSE, LLC
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at
# your option) any later version.
import asyncio
from datetime import datetime as dt
import logging
from typing import Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel
from libstuff.bench.plots import Histogram, Plots
from controllers.bench.types import (
    BenchConfig,
    BenchDBNS,
    BenchProgress,
    BenchResult,
    BenchTargetError,
)
from libstuff.dbm import DBM
from common.error import NoSuchRunError


class ResultTargetItem(BaseModel):
    name: str
    ops: List[str]


class ResultItem(BaseModel):
    uuid: UUID
    is_error: bool
    errors: List[BenchTargetError]
    progress: BenchProgress
    config: BenchConfig
    ops: List[ResultTargetItem]


class PlotEntry:
    last_access: dt
    plots: Dict[str, Plots]

    def __init__(self, last_access: dt, plots: Dict[str, Plots]) -> None:
        self.last_access = last_access
        self.plots = plots


class Results:

    _PLOTS_TTL: int = 600  # 10 minutes
    _GC_INTERVAL: int = 60  # 1 minute

    _results: Dict[UUID, ResultItem]
    _plots_lock: asyncio.Lock
    _plots: Dict[UUID, PlotEntry]

    _db: DBM
    _gc_task: Optional[asyncio.Task[None]]
    _stopping: bool
    logger: logging.Logger

    def __init__(
        self, db: DBM, logger: logging.Logger = logging.getLogger()
    ) -> None:
        self._results = {}
        self._plots_lock = asyncio.Lock()
        self._plots = {}
        self._db = db
        self._gc_task = None
        self._stopping = True
        self.logger = logger

    async def add(self, result: BenchResult) -> ResultItem:
        item = ResultItem(
            uuid=result.uuid,
            is_error=result.is_error,
            errors=result.errors,
            progress=result.progress,
            config=result.config,
            ops=[],
        )
        self._results[item.uuid] = item
        plot = await self._add_plot(result)
        for target, p in plot.plots.items():
            item.ops.append(ResultTargetItem(name=target, ops=p.get_ops()))

        return item

    async def start(self) -> None:
        self._stopping = False
        self._gc_task = asyncio.create_task(self._gc_task_fn())

    async def stop(self) -> None:
        if self._gc_task is None:
            return
        self._stopping = True
        await self._gc_task
        self._gc_task = None

    async def _gc(self) -> None:
        now = dt.now()
        async with self._plots_lock:
            to_delete: List[UUID] = []
            for uuid, entry in self._plots.items():
                td = now - entry.last_access
                if td.seconds >= self._PLOTS_TTL:
                    self.logger.info(f"drop plots for uuid {uuid}")
                    to_delete.append(uuid)

            for uuid in to_delete:
                del self._plots[uuid]

    async def _gc_task_fn(self) -> None:
        last_gc = dt.now()
        while not self._stopping:
            now = dt.now()
            td = now - last_gc
            if td.seconds >= self._GC_INTERVAL:
                await self._gc()
                last_gc = now
            await asyncio.sleep(1.0)

    async def _add_plot(self, result: BenchResult) -> PlotEntry:
        async with self._plots_lock:
            return await self._add_plot_unsafe(result)

    async def _add_plot_unsafe(self, result: BenchResult) -> PlotEntry:
        if result.uuid in self._plots:
            return self._plots[result.uuid]

        plots: Dict[str, Plots] = {}
        for target, res in result.results.items():
            plots[target] = Plots(res)

        entry = PlotEntry(last_access=dt.now(), plots=plots)
        self._plots[result.uuid] = entry
        return entry

    async def _load_plot(self, uuid: UUID) -> PlotEntry:
        async with self._plots_lock:
            if uuid in self._plots:
                entry = self._plots[uuid]
                entry.last_access = dt.now()
                return entry

            # load from dbm
            db_entry: Optional[BenchResult] = await self._db.get_model(
                ns=BenchDBNS.NS_RESULTS, key=str(uuid), model=BenchResult
            )
            if db_entry is None:
                raise NoSuchRunError()

            return await self._add_plot_unsafe(db_entry)

    async def get_histograms(
        self, uuid: UUID
    ) -> Dict[str, Dict[str, Histogram]]:
        histograms: Dict[str, Dict[str, Histogram]] = {}
        entry = await self._load_plot(uuid)
        for target, plot in entry.plots.items():
            histograms[target] = plot.get_latency_histogram_per_op()

        return histograms

    @property
    def results(self) -> Dict[UUID, ResultItem]:
        return self._results
