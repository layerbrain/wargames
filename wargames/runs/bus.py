from __future__ import annotations

import asyncio
from collections import defaultdict, deque
from collections.abc import AsyncIterator
from typing import Any


class RunBus:
    def __init__(self, *, max_tail: int = 200) -> None:
        self._max_tail = max_tail
        self._events: dict[str, deque[dict[str, Any]]] = defaultdict(lambda: deque(maxlen=max_tail))
        self._subscribers: dict[str, set[asyncio.Queue[dict[str, Any]]]] = defaultdict(set)

    def publish(self, run_id: str, event: dict[str, Any]) -> None:
        self._events[run_id].append(event)
        for queue in tuple(self._subscribers[run_id]):
            queue.put_nowait(event)

    def tail(self, run_id: str) -> tuple[dict[str, Any], ...]:
        return tuple(self._events[run_id])

    async def subscribe(self, run_id: str, *, replay_tail: bool = True) -> AsyncIterator[dict[str, Any]]:
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self._subscribers[run_id].add(queue)
        try:
            if replay_tail:
                for event in self.tail(run_id):
                    yield event
            while True:
                yield await queue.get()
        finally:
            self._subscribers[run_id].discard(queue)


run_bus = RunBus()
