"""Base class for optional application services."""

from __future__ import annotations

from abc import ABC, abstractmethod


class Service(ABC):
    """Component with an explicit asynchronous lifecycle."""

    name = "service"

    @abstractmethod
    async def start(self) -> None:
        """Start this service."""

    @abstractmethod
    async def stop(self) -> None:
        """Stop this service."""
