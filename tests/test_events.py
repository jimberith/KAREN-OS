import asyncio

from karenos.core.events import EventBus


def test_event_bus_delivers_payload():
    bus = EventBus()
    received = []

    async def handler(payload):
        received.append(payload["answer"])

    bus.subscribe("message", handler)
    asyncio.run(bus.publish("message", {"answer": 42}))
    assert received == [42]


def test_event_bus_unsubscribe():
    bus = EventBus()
    received = []

    async def handler(payload):
        received.append(payload)

    bus.subscribe("message", handler)
    bus.unsubscribe("message", handler)
    asyncio.run(bus.publish("message"))
    assert received == []
