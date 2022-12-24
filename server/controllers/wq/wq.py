# Copyright (C) 2022 SUSE, LLC
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at
# your option) any later version.

import abc
import asyncio
import copy
import logging
from collections import deque
from datetime import datetime as dt
from typing import Awaitable, Callable, List, Optional
from uuid import UUID, uuid4

from controllers.wq.progress import WQItemProgress
from controllers.wq.status import (
    WorkQueueState,
    WorkQueueStatus,
    WorkQueueStatusEntry,
    WorkQueueStatusItem,
)
from controllers.wq.types import (
    WQItemConfigType,
    WQItemKind,
    WQItemProgressType,
)


class WQItem(abc.ABC):

    _uuid: UUID
    _time_start: Optional[dt]
    _time_end: Optional[dt]
    _is_running: bool
    _is_done: bool
    logger: logging.Logger

    def __init__(self, logger: logging.Logger) -> None:
        self._uuid = uuid4()
        self._time_start = None
        self._time_end = None
        self._is_running = False
        self._is_done = False
        self.logger = logger

    @property
    def uuid(self) -> UUID:
        return self._uuid

    @property
    def time_start(self) -> Optional[dt]:
        return self._time_start

    @property
    def time_end(self) -> Optional[dt]:
        return self._time_end

    @property
    def duration(self) -> int:
        if self._time_start is None:
            return 0
        end = self._time_end if self._time_end is not None else dt.now()
        return (end - self._time_start).seconds

    @property
    def progress(self) -> WQItemProgress:
        return WQItemProgress(
            uuid=self.uuid,
            is_running=self._is_running,
            is_done=self._is_done,
            time_start=self._time_start,
            time_end=self._time_end,
            duration=self.duration,
            progress=self._progress,
        )

    def is_running(self) -> bool:
        return self._is_running

    def is_done(self) -> bool:
        return self._is_done

    async def run(self) -> None:
        assert not self._is_done
        assert self._time_end is None
        self._is_running = True
        self._time_start = dt.now()

        self.logger.debug(f"running work item uuid {self.uuid}")
        await self._run()
        self.logger.debug(f"done running work item uuid {self.uuid}")

        self._is_done = True
        self._is_running = False
        self._time_end = dt.now()

    async def stop(self) -> None:
        if not self._is_running:
            return

        await self._stop()
        self._is_running = False
        self._time_end = dt.now()

    @abc.abstractmethod
    async def _run(self) -> None:
        pass

    @abc.abstractmethod
    async def _stop(self) -> None:
        pass

    @property
    @abc.abstractmethod
    def _progress(self) -> Optional[WQItemProgressType]:
        pass

    @property
    @abc.abstractmethod
    def config(self) -> WQItemConfigType:
        pass


WQItemFinishCB = Callable[[WQItem], Awaitable[None]]
WQItemStartCB = Callable[[WQItem], Awaitable[None]]


class WQItemCB:
    start: WQItemStartCB
    finish: WQItemFinishCB

    def __init__(self, start: WQItemStartCB, finish: WQItemFinishCB) -> None:
        self.start = start
        self.finish = finish


class WQEntry:
    item: WQItem
    kind: WQItemKind
    cb: WQItemCB

    def __init__(self, item: WQItem, kind: WQItemKind, cb: WQItemCB) -> None:
        self.item = item
        self.kind = kind
        self.cb = cb


class WorkQueue:

    _lock: asyncio.Lock
    _task: Optional[asyncio.Task[None]]
    _is_shutting_down: bool
    _is_running: bool

    _waiting: deque[WQEntry]
    _running: Optional[WQEntry]
    _finished: List[WQEntry]

    _running_task: Optional[asyncio.Task[None]]

    logger: logging.Logger

    def __init__(self, logger: logging.Logger = logging.getLogger()) -> None:
        self._lock = asyncio.Lock()
        self._task = None
        self._is_shutting_down = False
        self._is_running = False
        self._waiting = deque()
        self._running = None
        self._finished = []
        self._running_task = None
        self.logger = logger

    async def start(self) -> None:
        async with self._lock:
            if self._is_shutting_down:
                self.logger.info("already shutting down.")
                return
            self.logger.info("starting workqueue")
            self._task = asyncio.create_task(self._tick())
            self._is_running = True

    async def stop(self) -> None:
        async with self._lock:
            if self._is_shutting_down:
                return
            self.logger.info("shutting down.")
            self._is_shutting_down = True

    async def _tick(self) -> None:
        while True:
            async with self._lock:
                if self._is_shutting_down:
                    await self._shutdown_queue()
                    break
                await self._handle_queue()

            await asyncio.sleep(1.0)

        self.logger.info("stopping main task, shutting down.")
        self._is_running = False

    async def _handle_queue(self) -> None:
        if self._running is None:
            await self._maybe_promote()
            return

        if self._running.item.is_done():
            item = self._running
            assert self._running_task is not None
            await self._running_task
            self._running = None
            self._running_task = None
            self._finished.append(item)
            await item.cb.finish(item.item)

    async def _maybe_promote(self) -> None:
        assert self._running is None
        if len(self._waiting) == 0:
            return

        next = self._waiting.popleft()
        self.logger.debug(f"promoting entry to running, kind: {next.kind}")
        await self._run_entry(next)

    async def _run_entry(self, entry: WQEntry) -> None:
        self._running = entry
        self._running_task = asyncio.create_task(entry.item.run())
        await self._running.cb.start(self._running.item)

    async def _shutdown_queue(self) -> None:
        self._waiting.clear()
        if self._running is None:
            return
        await self._running.item.stop()
        self._running = None

    async def put(self, item: WQItem, kind: WQItemKind, cb: WQItemCB) -> None:
        async with self._lock:
            if self._is_shutting_down:
                return
            self.logger.debug(f"append work item, kind: {kind}")
            self._waiting.append(WQEntry(item, kind, cb))

    async def waiting(self) -> List[WQEntry]:
        async with self._lock:
            lst = self._waiting.copy()
        return list(lst)

    async def finished(self) -> List[WQEntry]:
        async with self._lock:
            lst = self._finished.copy()
        return lst

    async def running(self) -> Optional[WQEntry]:
        ret: Optional[WQEntry] = None
        async with self._lock:
            if self._running is not None:
                ret = copy.copy(self._running)
        return ret

    def _convert_to_status_item(self, entry: WQEntry) -> WorkQueueStatusItem:
        return WorkQueueStatusItem(
            uuid=entry.item.uuid,
            kind=entry.kind,
            is_running=entry.item.is_running(),
            is_done=entry.item.is_done(),
            time_start=entry.item.time_start,
            time_end=entry.item.time_end,
            duration=entry.item.duration,
        )

    async def state(self) -> WorkQueueState:
        waiting: List[WorkQueueStatusItem] = []
        finished: List[WorkQueueStatusItem] = []
        current: Optional[WorkQueueStatusItem] = None

        async with self._lock:
            for entry in self._waiting:
                waiting.append(self._convert_to_status_item(entry))

            for entry in self._finished:
                finished.append(self._convert_to_status_item(entry))

            if self._running is not None:
                current = self._convert_to_status_item(self._running)

        return WorkQueueState(
            waiting=waiting, finished=finished, current=current
        )

    async def status(self) -> WorkQueueStatus:
        current: Optional[WQEntry] = await self.running()

        if current is None:
            return WorkQueueStatus(is_running=False, current=None)

        return WorkQueueStatus(
            is_running=True,
            current=WorkQueueStatusEntry(
                item=self._convert_to_status_item(current),
                progress=current.item.progress,
                config=current.item.config,
            ),
        )
