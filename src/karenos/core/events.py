"""Small asynchronous publish/subscribe event bus."""

from __future__ import annotations

import asyncio
from collections import defaultdict
from collections.abc import Awaitable, Callable
from typing import Any

EventHandler = Callable[[dict[str, Any]], Awaitable[None]]


class EventBus:
    """Dispatch events to async subscribers in registration order."""

    def __init__(self) -> None:
        self._handlers: dict[str, list[EventHandler]] = defaultdict(list)

    def subscribe(self, event_name: str, handler: EventHandler) -> None:
        if handler not in self._handlers[event_name]:
            self._handlers[event_name].append(handler)

    def unsubscribe(self, event_name: str, handler: EventHandler) -> None:
        if handler in self._handlers.get(event_name, []):
            self._handlers[event_name].remove(handler)

    async def publish(self, event_name: str, payload: dict[str, Any] | None = None) -> None:
        event = payload if payload is not None else {}
        for handler in tuple(self._handlers.get(event_name, [])):
            await handler(event)

    def publish_background(
        self, event_name: str, payload: dict[str, Any] | None = None
    ) -> asyncio.Task[None]:
        """Schedule an event in the currently running asyncio loop."""
        return asyncio.create_task(self.publish(event_name, payload))
