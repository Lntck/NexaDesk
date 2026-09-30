from datetime import datetime, timezone

from app.enums import ActivityEventType
from app.events.sse import HEARTBEAT_FRAME, project_channel, sse_frame
from app.models import ActivityEvent, User
from app.schemas.event import EventActor, RealtimeEvent


def make_event(**overrides) -> RealtimeEvent:
    """Build a realtime envelope with sensible defaults.

    Args:
        overrides: fields replacing the defaults.

    Returns:
        RealtimeEvent: envelope for assertions.
    """
    values = {
        "id": "01928b7e-0000-7000-8000-000000000001",
        "type": ActivityEventType.TASK_STATUS_CHANGED,
        "project_id": 42,
        "task_id": 123,
        "actor": EventActor(id=7, username="rush"),
        "timestamp": datetime(2026, 9, 29, 17, 0, tzinfo=timezone.utc),
        "data": {"from": "TODO", "to": "IN_PROGRESS"},
    }
    values.update(overrides)
    return RealtimeEvent(**values)


def test_frame_matches_contract_format():
    """SSE frame carries event type, id and the JSON envelope."""
    frame = sse_frame(make_event()).decode("utf-8")

    assert frame.startswith("event: task.status_changed\n")
    assert "id: 01928b7e-0000-7000-8000-000000000001\n" in frame
    data_line = frame.splitlines()[2]
    assert data_line.startswith("data: {")
    assert '"username":"rush"' in data_line
    assert frame.endswith("\n\n")


def test_heartbeat_frame_is_a_comment():
    """Heartbeat is an SSE comment so clients ignore it."""
    assert HEARTBEAT_FRAME == b": heartbeat\n\n"


def test_project_channel_naming():
    """Channel names are stable and project scoped."""
    assert project_channel(42) == "nexadesk:events:project:42"


def test_from_activity_maps_stored_entry():
    """Envelope built from history row keeps actor and scope."""
    user = User(
        id=7,
        username="rush",
        email="rush@example.com",
        password_hash="x",
        is_active=True,
    )
    row = ActivityEvent(
        id="01928b7e-0000-7000-8000-000000000002",
        type=ActivityEventType.COMMENT_CREATED,
        project_id=42,
        task_id=123,
        actor_id=7,
        data={"comment_id": 5},
        created_at=datetime(2026, 9, 29, 17, 0, tzinfo=timezone.utc),
    )
    row.actor = user

    event = RealtimeEvent.from_activity(row)

    assert event.id == row.id
    assert event.type == ActivityEventType.COMMENT_CREATED
    assert event.project_id == 42
    assert event.task_id == 123
    assert event.actor == EventActor(id=7, username="rush")
    assert event.data == {"comment_id": 5}
    assert event.timestamp == row.created_at


def test_from_activity_without_actor():
    """Envelope without a resolvable actor omits the actor block."""
    row = ActivityEvent(
        id="01928b7e-0000-7000-8000-000000000003",
        type=ActivityEventType.TASK_CREATED,
        project_id=42,
        task_id=None,
        actor_id=None,
        data={},
        created_at=datetime(2026, 9, 29, 17, 0, tzinfo=timezone.utc),
    )

    event = RealtimeEvent.from_activity(row)

    assert event.actor is None
    assert event.task_id is None
