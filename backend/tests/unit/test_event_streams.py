import asyncio
from datetime import datetime, timezone

import pytest
from fakeredis.aioredis import FakeRedis

from app.enums import ActivityEventType, NotificationDeliveryType
from app.events import DomainEvent
from app.events.publisher import RedisPublisher
from app.events.sse import HEARTBEAT_FRAME, project_channel
from app.events.streams import (
    ConnectionManager,
    StreamConnection,
    _feed_events,
    _watch_idle,
    project_event_stream,
)
from app.models import ActivityEvent
from app.schemas.event import EventActor, RealtimeEvent
from tests.fakes.activity_crud import FakeActivityCRUD
from tests.fakes.domain import DomainStore


def make_realtime_event(event_id: str, **overrides) -> RealtimeEvent:
    """Build a realtime envelope with sensible defaults.

    Args:
        event_id: opaque event id.
        overrides: fields replacing the defaults.

    Returns:
        RealtimeEvent: envelope for assertions.
    """
    values = {
        "id": event_id,
        "type": ActivityEventType.TASK_STATUS_CHANGED,
        "project_id": 42,
        "task_id": 123,
        "actor": EventActor(id=7, username="rush"),
        "timestamp": datetime(2026, 9, 29, 17, 0, tzinfo=timezone.utc),
        "data": {"to": "IN_PROGRESS"},
    }
    values.update(overrides)
    return RealtimeEvent(**values)


class DownRedis:
    """Redis client whose broker access always fails."""

    def pubsub(self):
        """Refuse to hand out a subscription.

        Raises:
            ConnectionError: always.
        """
        raise ConnectionError("broker is down")


async def wait_until_subscribed(fake: FakeRedis, channel: str) -> None:
    """Block until a subscriber is registered on a channel.

    Args:
        fake: shared fake broker.
        channel: channel the stream should subscribe to.

    Raises:
        AssertionError: when nobody subscribes in time.
    """
    for _ in range(200):
        stats = await fake.pubsub_numsub(channel)
        if stats and stats[0][1] > 0:
            return
        await asyncio.sleep(0.01)
    raise AssertionError("stream did not subscribe to the project channel")


def test_manager_replaces_previous_stream():
    """A second stream of the same client closes the first one."""
    manager = ConnectionManager()

    first = manager.register(1, 42, max_queued_events=10)
    second = manager.register(1, 42, max_queued_events=10)

    assert first.closed
    assert manager.get(1, 42) is second
    assert manager.count() == 1

    manager.unregister(first)
    assert manager.get(1, 42) is second


def test_enqueue_overflow_closes_connection():
    """A queue bound to two frames refuses the third and closes."""
    manager = ConnectionManager()
    connection = manager.register(1, 42, max_queued_events=2)

    assert connection.enqueue(b"one\n\n") is True
    assert connection.enqueue(b"two\n\n") is True
    assert connection.enqueue(b"three\n\n") is False

    assert connection.overflowed
    assert connection.closed


@pytest.mark.asyncio
async def test_next_frame_times_out_or_wakes_on_close():
    """Frame waits end with None on timeout or close."""
    manager = ConnectionManager()
    connection = manager.register(1, 42, max_queued_events=10)

    assert await connection.next_frame(0.01) is None

    waiter = asyncio.create_task(connection.next_frame(5))
    await asyncio.sleep(0.01)
    connection.request_close()
    assert await asyncio.wait_for(waiter, timeout=1) is None


@pytest.mark.asyncio
async def test_stream_replays_missed_events():
    """Replay frames are served before anything live."""
    manager = ConnectionManager()
    replay = [
        make_realtime_event("01928b7e-0000-7000-8000-000000000020"),
        make_realtime_event("01928b7e-0000-7000-8000-000000000021"),
    ]
    stream = project_event_stream(
        manager=manager,
        redis_client=FakeRedis(),
        project_id=42,
        user_id=1,
        replay=replay,
        heartbeat_s=5.0,
    )

    first = await asyncio.wait_for(anext(stream), timeout=1)
    second = await asyncio.wait_for(anext(stream), timeout=1)

    assert b"id: 01928b7e-0000-7000-8000-000000000020" in first
    assert b"id: 01928b7e-0000-7000-8000-000000000021" in second
    await stream.aclose()
    assert manager.count() == 0


@pytest.mark.asyncio
async def test_stream_delivers_live_events():
    """Broker messages become SSE frames on the open stream."""
    fake = FakeRedis()
    publisher = RedisPublisher(client=fake, actor_lookup=None)
    manager = ConnectionManager()
    stream = project_event_stream(
        manager=manager,
        redis_client=fake,
        project_id=42,
        user_id=1,
        heartbeat_s=5.0,
    )

    waiter = asyncio.create_task(anext(stream))
    await wait_until_subscribed(fake, project_channel(42))
    await publisher.publish(
        DomainEvent(
            id="01928b7e-0000-7000-8000-000000000030",
            type=ActivityEventType.TASK_STATUS_CHANGED.value,
            project_id=42,
            task_id=123,
            actor_id=7,
            data={"to": "IN_PROGRESS"},
        )
    )

    frame = await asyncio.wait_for(waiter, timeout=2)
    assert b"event: task.status_changed" in frame
    assert b"id: 01928b7e-0000-7000-8000-000000000030" in frame

    await stream.aclose()
    await fake.aclose()


@pytest.mark.asyncio
async def test_stream_sends_heartbeats_when_idle():
    """An idle stream keeps the connection alive with comments."""
    manager = ConnectionManager()
    stream = project_event_stream(
        manager=manager,
        redis_client=FakeRedis(),
        project_id=42,
        user_id=1,
        heartbeat_s=0.05,
    )

    frame = await asyncio.wait_for(anext(stream), timeout=2)

    assert frame == HEARTBEAT_FRAME
    await stream.aclose()


@pytest.mark.asyncio
async def test_stream_survives_broker_failure():
    """Without a broker the stream still serves replayed events."""
    manager = ConnectionManager()
    replay = [make_realtime_event("01928b7e-0000-7000-8000-000000000040")]
    stream = project_event_stream(
        manager=manager,
        redis_client=DownRedis(),
        project_id=42,
        user_id=1,
        replay=replay,
        heartbeat_s=5.0,
    )

    frame = await asyncio.wait_for(anext(stream), timeout=1)

    assert b"id: 01928b7e-0000-7000-8000-000000000040" in frame
    await stream.aclose()


@pytest.mark.asyncio
async def test_watch_idle_closes_stalled_stream():
    """A stream without progress is retired after the idle timeout."""
    manager = ConnectionManager()
    connection = manager.register(1, 42, max_queued_events=10)

    watchdog = asyncio.create_task(_watch_idle(connection, idle_timeout_s=0.1))
    await asyncio.sleep(0.35)

    assert connection.closed
    watchdog.cancel()


@pytest.mark.asyncio
async def test_replay_rows_after_id():
    """History replay returns the newest rows in id order."""
    crud = FakeActivityCRUD(DomainStore())
    for index in range(1, 4):
        await crud.create_event(
            None,
            ActivityEvent(
                id=f"01928b7e-0000-7000-8000-00000000005{index}",
                type=ActivityEventType.TASK_CREATED,
                project_id=42,
                task_id=None,
                actor_id=7,
                data={},
                created_at=datetime(2026, 9, 29, 17, index, tzinfo=timezone.utc),
            ),
        )

    after_id = "01928b7e-0000-7000-8000-000000000051"
    rows = await crud.list_events_after(None, 42, after_id, 10)

    assert [row.id for row in rows] == [
        "01928b7e-0000-7000-8000-000000000052",
        "01928b7e-0000-7000-8000-000000000053",
    ]
    limited = await crud.list_events_after(None, 42, after_id, 1)
    assert [row.id for row in limited] == ["01928b7e-0000-7000-8000-000000000052"]


def drain(connection) -> list[bytes]:
    """Collect the frames queued for one stream.

    Args:
        connection: stream whose queue is drained.

    Returns:
        list[bytes]: queued SSE frames in delivery order.
    """
    frames = []
    while not connection.queue.empty():
        frames.append(connection.queue.get_nowait())
    return frames


@pytest.mark.asyncio
async def test_feed_delivers_notifications_to_recipient_only():
    """Notification frames reach only the addressed user's stream."""
    fake = FakeRedis()
    mine = StreamConnection(user_id=5, project_id=42, max_queued_events=10)
    theirs = StreamConnection(user_id=6, project_id=42, max_queued_events=10)
    pubsub_one = fake.pubsub()
    pubsub_two = fake.pubsub()
    await pubsub_one.subscribe(project_channel(42))
    await pubsub_two.subscribe(project_channel(42))
    feed_one = asyncio.create_task(_feed_events(mine, pubsub_one))
    feed_two = asyncio.create_task(_feed_events(theirs, pubsub_two))
    await wait_until_subscribed(fake, project_channel(42))

    notification = make_realtime_event(
        "01928b7e-0000-7000-8000-000000000060",
        type=NotificationDeliveryType.NOTIFICATION_CREATED,
        recipient_id=5,
        data={"id": 3},
    )
    await fake.publish(project_channel(42), notification.model_dump_json())
    await fake.publish(
        project_channel(42),
        make_realtime_event("01928b7e-0000-7000-8000-000000000061").model_dump_json(),
    )
    await asyncio.sleep(0.2)

    mine_frames = drain(mine)
    assert len(mine_frames) == 2
    assert b"notification.created" in mine_frames[0]
    assert len(drain(theirs)) == 1
    for task in (feed_one, feed_two):
        task.cancel()
    await pubsub_one.aclose()
    await pubsub_two.aclose()
    await fake.aclose()
