"""Start and stop application services safely."""

from __future__ import annotations

import logging

from karenos.core.service import Service

logger = logging.getLogger(__name__)


class ServiceManager:
    """Starts in registration order and stops already-started services in reverse."""

    def __init__(self) -> None:
        self._services: list[Service] = []
        self._started: list[Service] = []

    def register(self, service: Service) -> None:
        if any(item.name == service.name for item in self._services):
            raise ValueError(f"Service name already registered: {service.name}")
        self._services.append(service)

    async def start_all(self) -> None:
        try:
            for service in self._services:
                await service.start()
                self._started.append(service)
                logger.info("Started service %s", service.name)
        except Exception:
            await self.stop_all()
            raise

    async def stop_all(self) -> None:
        while self._started:
            service = self._started.pop()
            try:
                await service.stop()
                logger.info("Stopped service %s", service.name)
            except Exception:
                logger.exception("Failed to stop service %s", service.name)
