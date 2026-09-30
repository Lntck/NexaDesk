"""Redis Pub/Sub delivery backend for domain events.

The publisher is the Redis backed implementation of the ``EventPublisher``
seam introduced in Phase 0: services keep queueing events on the session,
the request dependency drains them strictly after commit and hands them to
this publisher, which broadcasts JSON envelopes to the per-project channel
consumed by the SSE streams.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Protocol

from sqlalchemy import select

from app.core.logger import logger
from app.enums import ActivityEventType, NotificationDeliveryType
from app.events import DomainEvent, NotificationDelivery, new_event_id
from app.events.sse import project_channel
from app.models import User
from app.schemas.event import EventActor, RealtimeEvent
from app.utils import utcnow

if TYPE_CHECKING:
    from redis.asyncio import Redis

    from app.db import DatabaseClient


class ActorLookup(Protocol):
    """Resolution of actor usernames for realtime envelopes."""

    async def username(self, actor_id: int) -> str | None:
        """Return the username of one account.

        Args:
            actor_id: id of the account to resolve.

        Returns:
            str | None: username, or None when the account is gone.
        """
        ...


class DatabaseActorLookup:
    """Actor usernames read from the database."""

    def __init__(self, db: DatabaseClient):
        """Attach the database.

        Args:
            db: database client whose session factory reads usernames.
        """
        self.db = db

    async def username(self, actor_id: int) -> str | None:
        """Return the username of one account.

        Args:
            actor_id: id of the account to resolve.

        Returns:
            str | None: username, or None when the account does not exist.
        """
        async with self.db.session_factory() as session:
            stmt = select(User.username).where(User.id == actor_id)
            name: str | None = await session.scalar(stmt)
            return name


class RedisPublisher:
    """Broadcast domain events to per-project Redis channels.

    Delivery is best effort by design: a failing broker must never break
    the REST request that triggered the event. The persisted
    ``activity_events`` rows remain the source of truth for replay.
    """

    def __init__(
        self,
        client: Redis,
        actor_lookup: ActorLookup | None = None,
        actor_cache_ttl: float = 300.0,
    ):
        """Attach the broker and the optional actor resolution.

        Args:
            client: asynchronous Redis client used for PUBLISH.
            actor_lookup: resolver for actor usernames, None to send
                events without an actor block.
            actor_cache_ttl: lifetime of one cached username in seconds.
        """
        self.client = client
        self.actor_lookup = actor_lookup
        self.actor_cache_ttl = actor_cache_ttl
        self._actor_cache: dict[int, tuple[float, str | None]] = {}

    async def publish(self, event: DomainEvent) -> None:
        """Publish one domain event to its project channel.

        Events without a project scope have no stream audience yet and are
        skipped. Every notification attached to the event is published as
        its own ``notification.created`` frame carrying the recipient, so
        streams can drop it for everyone else. Broker and lookup failures
        are logged and swallowed.

        Args:
            event: domain event queued during the committed transaction.
        """
        if event.project_id is None:
            return
        try:
            envelope = await self._build_envelope(event)
            channel = project_channel(event.project_id)
            await self.client.publish(channel, envelope.model_dump_json())
            for delivery in event.notifications:
                frame = self._notification_frame(envelope, delivery)
                await self.client.publish(channel, frame.model_dump_json())
        except Exception as exc:
            logger.warning("event publish failed for %s: %s", event.type, exc)

    @staticmethod
    def _notification_frame(
        envelope: RealtimeEvent, delivery: NotificationDelivery
    ) -> RealtimeEvent:
        """Build the recipient-scoped notification frame of one event.

        The frame reuses the id of the source activity entry, so the SSE
        replay cursor stays a single sortable sequence.

        Args:
            envelope: envelope of the source domain event.
            delivery: recipient and rendered notification payload.

        Returns:
            RealtimeEvent: notification.created envelope.
        """
        return RealtimeEvent(
            id=envelope.id,
            type=NotificationDeliveryType.NOTIFICATION_CREATED,
            project_id=envelope.project_id,
            task_id=envelope.task_id,
            actor=envelope.actor,
            recipient_id=delivery.user_id,
            timestamp=envelope.timestamp,
            data=delivery.payload,
        )

    async def _build_envelope(self, event: DomainEvent) -> RealtimeEvent:
        """Convert a domain event into its wire envelope.

        Args:
            event: domain event queued during the transaction.

        Returns:
            RealtimeEvent: envelope with resolved actor and timestamp.
        """
        return RealtimeEvent(
            id=event.id or new_event_id(),
            type=ActivityEventType(event.type),
            project_id=event.project_id,
            task_id=event.task_id,
            actor=await self._resolve_actor(event.actor_id),
            timestamp=utcnow(),
            data=dict(event.data),
        )

    async def _resolve_actor(self, actor_id: int | None) -> EventActor | None:
        """Resolve the actor block of an envelope.

        Usernames are cached for a while: active actors repeat across
        events, so live delivery stays free of per-event user queries.

        Args:
            actor_id: id of the user who caused the event.

        Returns:
            EventActor | None: actor block, None without an actor.
        """
        if actor_id is None:
            return None
        username = await self._cached_username(actor_id)
        return EventActor(id=actor_id, username=username or "")

    async def _cached_username(self, actor_id: int) -> str | None:
        """Return one username through the TTL cache.

        Args:
            actor_id: id of the account to resolve.

        Returns:
            str | None: username, or None when the account is gone.
        """
        cached = self._actor_cache.get(actor_id)
        if cached is not None and cached[0] > time.monotonic():
            return cached[1]
        username = None
        if self.actor_lookup is not None:
            username = await self.actor_lookup.username(actor_id)
        expires = time.monotonic() + self.actor_cache_ttl
        self._actor_cache[actor_id] = (expires, username)
        return username
