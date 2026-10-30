import asyncio

import pytest

from karenos.core.service import Service
from karenos.core.service_manager import ServiceManager


class DemoService(Service):
    def __init__(self, name, events, should_fail=False):
        self.name = name
        self.events = events
        self.should_fail = should_fail

    async def start(self):
        self.events.append(f"start:{self.name}")
        if self.should_fail:
            raise RuntimeError("service start failed")

    async def stop(self):
        self.events.append(f"stop:{self.name}")


def test_services_stop_in_reverse_order():
    events = []
    manager = ServiceManager()
    manager.register(DemoService("first", events))
    manager.register(DemoService("second", events))

    asyncio.run(manager.start_all())
    asyncio.run(manager.stop_all())

    assert events == [
        "start:first", "start:second", "stop:second", "stop:first"
    ]


def test_failed_start_rolls_back_started_services():
    events = []
    manager = ServiceManager()
    manager.register(DemoService("first", events))
    manager.register(DemoService("broken", events, should_fail=True))

    with pytest.raises(RuntimeError):
        asyncio.run(manager.start_all())

    assert events == ["start:first", "start:broken", "stop:first"]


def test_duplicate_service_names_are_rejected():
    manager = ServiceManager()
    manager.register(DemoService("duplicate", []))
    with pytest.raises(ValueError):
        manager.register(DemoService("duplicate", []))
