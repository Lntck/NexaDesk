"""Per-project SSE streams and their connection registry.

One stream serves one (client, project) pair. The registry enforces a
single stream per client per project, the bounded queue protects the
process from slow consumers and the watchdog retires streams whose
writes stall, all as described in docs/api-endpoints.md, section 25.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, AsyncGenerator, Sequence

from app.core.logger import logger
from app.events.sse import HEARTBEAT_FRAME, project_channel, sse_frame
from app.schemas.event import RealtimeEvent

if TYPE_CHECKING:
    from redis.asyncio import Redis
    from redis.asyncio.client import PubSub


@dataclass
class StreamConnection:
    """One open SSE stream of a single client inside one project."""

    user_id: int
    project_id: int
    max_queued_events: int
    queue: asyncio.Queue[bytes] = field(init=False)
    close_event: asyncio.Event = field(init=False)
    overflowed: bool = False
    last_activity: float = field(default_factory=time.monotonic)

    def __post_init__(self) -> None:
        """Create the bounded queue and the close signal."""
        self.queue = asyncio.Queue(maxsize=self.max_queued_events)
        self.close_event = asyncio.Event()

    def enqueue(self, frame: bytes) -> bool:
        """Queue one frame for the client.

        A full queue means the client cannot keep up; the stream is marked
        as overflowed and closed so the client reconnects with replay.

        Args:
            frame: encoded SSE frame.

        Returns:
            bool: True when queued, False when the stream must close.
        """
        try:
            self.queue.put_nowait(frame)
            return True
        except asyncio.QueueFull:
            self.overflowed = True
            self.request_close()
            return False

    def request_close(self) -> None:
        """Signal the stream loop to stop after its current frame."""
        self.close_event.set()

    @property
    def closed(self) -> bool:
        """Report whether the stream was asked to stop.

        Returns:
            bool: True once close was requested.
        """
        return self.close_event.is_set()

    def mark_activity(self) -> None:
        """Record successful stream progress for the idle watchdog."""
        self.last_activity = time.monotonic()

    async def next_frame(self, timeout: float) -> bytes | None:
        """Wait for the next frame, the close signal or a timeout.

        Args:
            timeout: seconds to wait before giving up.

        Returns:
            bytes | None: next queued frame, or None on timeout or close.
        """
        if self.closed:
            return None
        get_task = asyncio.create_task(self.queue.get())
        close_task = asyncio.create_task(self.close_event.wait())
        try:
            await asyncio.wait(
                {get_task, close_task},
                timeout=timeout,
                return_when=asyncio.FIRST_COMPLETED,
            )
        finally:
            for task in (get_task, close_task):
                if not task.done():
                    task.cancel()
        if get_task.done() and not get_task.cancelled():
            return get_task.result()
        return None


class ConnectionManager:
    """Registry of open SSE streams with per-client exclusivity."""

    def __init__(self) -> None:
        """Create an empty registry."""
        self._streams: dict[tuple[int, int], StreamConnection] = {}

    def register(
        self, user_id: int, project_id: int, max_queued_events: int
    ) -> StreamConnection:
        """Open a stream slot for one client inside one project.

        A second stream for the same pair replaces the first one: the
        previous connection is asked to close.

        Args:
            user_id: authenticated client.
            project_id: project being streamed.
            max_queued_events: per-stream queue bound.

        Returns:
            StreamConnection: the newly registered connection.
        """
        previous = self._streams.get((user_id, project_id))
        if previous is not None:
            previous.request_close()
        connection = StreamConnection(
            user_id=user_id,
            project_id=project_id,
            max_queued_events=max_queued_events,
        )
        self._streams[(user_id, project_id)] = connection
        return connection

    def unregister(self, connection: StreamConnection) -> None:
        """Remove a stream from the registry.

        Removing a replaced stream leaves the newer registration intact.

        Args:
            connection: stream that finished.
        """
        key = (connection.user_id, connection.project_id)
        if self._streams.get(key) is connection:
            del self._streams[key]

    def get(self, user_id: int, project_id: int) -> StreamConnection | None:
        """Return the open stream of one client in one project.

        Args:
            user_id: authenticated client.
            project_id: project being streamed.

        Returns:
            StreamConnection | None: registered stream, if any.
        """
        return self._streams.get((user_id, project_id))

    def count(self) -> int:
        """Count open streams across all projects.

        Returns:
            int: number of registered connections.
        """
        return len(self._streams)


async def _feed_events(connection: StreamConnection, pubsub: PubSub) -> None:
    """Pump live broker messages into the stream queue.

    Notification frames are addressed to one user and are dropped for
    every other stream of the project.

    Args:
        connection: stream to feed.
        pubsub: subscribed Redis Pub/Sub handle.

    """
    try:
        async for message in pubsub.listen():
            if message.get("type") != "message":
                continue
            payload = message.get("data") or b""
            try:
                event = RealtimeEvent.model_validate_json(payload)
            except Exception:
                logger.warning("dropping malformed realtime event: %r", payload)
                continue
            if (
                event.recipient_id is not None
                and event.recipient_id != connection.user_id
            ):
                continue
            if not connection.enqueue(sse_frame(event)):
                return
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        logger.warning("realtime feed stopped: %s", exc)
        connection.request_close()


async def _watch_idle(connection: StreamConnection, idle_timeout_s: float) -> None:
    """Close a stream whose loop stopped making progress.

    A healthy stream marks activity every heartbeat; a stream blocked on a
    stalled client write does not and is retired after the timeout.

    Args:
        connection: stream to supervise.
        idle_timeout_s: seconds without stream progress before closing.

    """
    while not connection.closed:
        await asyncio.sleep(idle_timeout_s / 2)
        if time.monotonic() - connection.last_activity > idle_timeout_s:
            connection.request_close()
            return


async def project_event_stream(
    manager: ConnectionManager,
    redis_client: Redis,
    project_id: int,
    user_id: int,
    replay: Sequence[RealtimeEvent] = (),
    heartbeat_s: float = 15.0,
    idle_timeout_s: float = 300.0,
    max_queued_events: int = 10000,
) -> AsyncGenerator[bytes, None]:
    """Stream one project event feed to one client.

    The generator replays missed events first, then interleaves live
    events from the Redis channel with heartbeat comments. It ends when the
    client disconnects, when the queue overflows or when the idle watchdog
    retires the stream.

    Args:
        manager: registry owning the connection slot.
        redis_client: broker delivering live project events.
        project_id: project being streamed.
        user_id: authenticated client owning the stream.
        replay: events missed while the client was away.
        heartbeat_s: interval between heartbeat comments.
        idle_timeout_s: seconds without progress before closing.
        max_queued_events: per-stream queue bound.

    Yields:
        bytes: encoded SSE frames.
    """
    connection = manager.register(user_id, project_id, max_queued_events)
    pubsub: PubSub | None = None
    feeder: asyncio.Task | None = None
    watchdog: asyncio.Task | None = None
    try:
        try:
            pubsub = redis_client.pubsub()
            await pubsub.subscribe(project_channel(project_id))
            feeder = asyncio.create_task(_feed_events(connection, pubsub))
        except Exception as exc:
            logger.warning(
                "realtime broker unavailable for project %s: %s", project_id, exc
            )
        watchdog = asyncio.create_task(_watch_idle(connection, idle_timeout_s))

        for event in replay:
            yield sse_frame(event)
            connection.mark_activity()

        while not connection.closed:
            frame = await connection.next_frame(heartbeat_s)
            connection.mark_activity()
            if frame is None:
                yield HEARTBEAT_FRAME
                continue
            yield frame
    finally:
        connection.request_close()
        for task in (feeder, watchdog):
            if task is not None:
                task.cancel()
        if pubsub is not None:
            try:
                await pubsub.aclose()
            except Exception:
                pass
        manager.unregister(connection)
