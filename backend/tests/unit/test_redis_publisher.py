import asyncio
import contextlib

import pytest
from fakeredis.aioredis import FakeRedis

from app.events import DomainEvent, NotificationDelivery
from app.events.publisher import RedisPublisher
from app.events.sse import project_channel
from app.schemas.event import RealtimeEvent

SECOND_ID = "01928b7e-0000-7000-8000-000000000011"
OTHER_ID = "01928b7e-0000-7000-8000-000000000012"


class StubLookup:
    """Counting actor lookup used to verify username resolution."""

    def __init__(self, names: dict[int, str] | None = None):
        """Attach the known usernames.

        Args:
            names: mapping of user id to username.
        """
        self.names = names or {}
        self.calls: list[int] = []

    async def username(self, actor_id: int) -> str | None:
        """Return a username and remember the lookup.

        Args:
            actor_id: id of the account to resolve.

        Returns:
            str | None: configured username, if any.
        """
        self.calls.append(actor_id)
        return self.names.get(actor_id)


async def collect_messages(pubsub, timeout: float = 0.2) -> list[dict]:
    """Gather broker messages published during a short window.

    Args:
        pubsub: subscribed fake broker handle.
        timeout: collection window in seconds.

    Returns:
        list[dict]: delivered messages in arrival order.
    """
    messages: list[dict] = []

    async def pump():
        """Drain the subscription until cancelled."""
        async for message in pubsub.listen():
            if message.get("type") == "message":
                messages.append(message)

    task = asyncio.create_task(pump())
    await asyncio.sleep(timeout)
    task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await task
    return messages


def make_domain_event(**overrides) -> DomainEvent:
    """Build a domain event with sensible defaults.

    Args:
        overrides: fields replacing the defaults.

    Returns:
        DomainEvent: event for assertions.
    """
    values = {
        "id": "01928b7e-0000-7000-8000-000000000010",
        "type": "task.status_changed",
        "project_id": 42,
        "task_id": 123,
        "actor_id": 7,
        "data": {"to": "IN_PROGRESS"},
    }
    values.update(overrides)
    return DomainEvent(**values)


class BrokenRedis:
    """Redis client failing every command."""

    async def publish(self, *args, **kwargs):
        """Fail like a broker that is down.

        Args:
            args: positional command arguments.
            kwargs: keyword command arguments.

        Raises:
            ConnectionError: always.
        """
        raise ConnectionError("broker is down")


@pytest.mark.asyncio
async def test_publish_delivers_envelope_to_project_channel():
    """Published events arrive on the project channel as JSON envelopes."""
    fake = FakeRedis()
    publisher = RedisPublisher(client=fake, actor_lookup=StubLookup({7: "rush"}))
    pubsub = fake.pubsub()
    await pubsub.subscribe(project_channel(42))

    await publisher.publish(make_domain_event())
    messages = await collect_messages(pubsub)

    assert len(messages) == 1
    event = RealtimeEvent.model_validate_json(messages[0]["data"])
    assert event.id == "01928b7e-0000-7000-8000-000000000010"
    assert event.type.value == "task.status_changed"
    assert event.project_id == 42
    assert event.task_id == 123
    assert event.actor is not None
    assert event.actor.username == "rush"
    assert event.data == {"to": "IN_PROGRESS"}
    await pubsub.aclose()
    await fake.aclose()


@pytest.mark.asyncio
async def test_notification_frames_carry_recipient():
    """Attached notifications are published as addressed frames."""
    fake = FakeRedis()
    publisher = RedisPublisher(client=fake, actor_lookup=StubLookup({7: "rush"}))
    pubsub = fake.pubsub()
    await pubsub.subscribe(project_channel(42))
    event = make_domain_event(
        notifications=(
            NotificationDelivery(
                user_id=5,
                payload={"id": 3, "type": "task.assigned", "is_read": False},
            ),
        )
    )

    await publisher.publish(event)
    messages = await collect_messages(pubsub)

    assert len(messages) == 2
    frame = RealtimeEvent.model_validate_json(messages[1]["data"])
    assert frame.type.value == "notification.created"
    assert frame.id == event.id
    assert frame.recipient_id == 5
    assert frame.data["id"] == 3
    assert RealtimeEvent.model_validate_json(messages[0]["data"]).recipient_id is None
    await pubsub.aclose()
    await fake.aclose()


@pytest.mark.asyncio
async def test_actor_username_is_resolved_once_and_cached():
    """Repeated events of one actor trigger a single lookup."""
    fake = FakeRedis()
    lookup = StubLookup({7: "rush"})
    publisher = RedisPublisher(client=fake, actor_lookup=lookup)

    await publisher.publish(make_domain_event())
    await publisher.publish(make_domain_event(id=SECOND_ID))

    assert lookup.calls == [7]
    await fake.aclose()


@pytest.mark.asyncio
async def test_event_without_project_is_skipped():
    """Global events have no stream audience and are not broadcast."""
    fake = FakeRedis()
    publisher = RedisPublisher(client=fake, actor_lookup=StubLookup())
    pubsub = fake.pubsub()
    await pubsub.subscribe(project_channel(42))

    await publisher.publish(make_domain_event(project_id=None))
    await publisher.publish(make_domain_event(id=OTHER_ID))
    messages = await collect_messages(pubsub)

    assert [RealtimeEvent.model_validate_json(m["data"]).id for m in messages] == [
        OTHER_ID
    ]
    await pubsub.aclose()
    await fake.aclose()


@pytest.mark.asyncio
async def test_broker_failure_is_swallowed():
    """A failing broker never breaks the request that emitted the event."""
    publisher = RedisPublisher(client=BrokenRedis(), actor_lookup=StubLookup())

    await publisher.publish(make_domain_event())
