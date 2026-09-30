"""SSE framing and realtime channel naming.

The frame format follows docs/api-endpoints.md, section 21: one ``event:``
line with the event type key, one ``id:`` line with the opaque event id
(replayed back as ``Last-Event-ID`` on reconnect) and one ``data:`` line
carrying the JSON envelope.
"""

from __future__ import annotations

from app.schemas.event import RealtimeEvent

PROJECT_CHANNEL_PREFIX = "nexadesk:events:project:"

#: Keep-alive comment sent between events so proxies do not drop the stream.
HEARTBEAT_FRAME: bytes = b": heartbeat\n\n"


def project_channel(project_id: int) -> str:
    """Return the Redis Pub/Sub channel of one project event stream.

    Args:
        project_id: project whose events are distributed.

    Returns:
        str: channel name shared by the publisher and the SSE streams.
    """
    return f"{PROJECT_CHANNEL_PREFIX}{project_id}"


def sse_frame(event: RealtimeEvent) -> bytes:
    """Encode one realtime event as an SSE frame.

    Args:
        event: envelope to place on the wire.

    Returns:
        bytes: frame terminated by a blank line, ready to stream.
    """
    return (
        f"event: {event.type.value}\n"
        f"id: {event.id}\n"
        f"data: {event.model_dump_json()}\n\n"
    ).encode("utf-8")
