"""Top-level application lifecycle."""

from __future__ import annotations

import asyncio

from karenos.core.events import EventBus
from karenos.core.service_manager import ServiceManager


class KarenApplication:
    """Owns the event bus and registered background services."""

    def __init__(self) -> None:
        self.events = EventBus()
        self.services = ServiceManager()

    async def start(self) -> None:
        await self.services.start_all()

    async def stop(self) -> None:
        await self.services.stop_all()

    def run_lifecycle_check(self) -> None:
        """Start and stop registered services, useful for a simple smoke test."""
        async def run() -> None:
            await self.start()
            await self.stop()

        asyncio.run(run())
