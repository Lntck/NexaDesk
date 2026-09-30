from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core import get_settings
from app.db import DatabaseClient, RedisClient
from app.events.publisher import DatabaseActorLookup, RedisPublisher
from app.events.streams import ConnectionManager


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Build shared infrastructure on startup and dispose it on shutdown.

    The database client, the Redis client, the realtime event publisher
    and the SSE connection registry live on app.state for the whole
    process lifetime.

    Args:
        app: application being started.

    Yields:
        None: control to the running application.
    """
    settings = get_settings()

    app.state.db = DatabaseClient(
        url=settings.database_url,
    )

    app.state.redis = RedisClient(
        url=settings.redis_url,
    )

    app.state.publisher = RedisPublisher(
        client=app.state.redis.get_client(),
        actor_lookup=DatabaseActorLookup(app.state.db),
    )

    app.state.connections = ConnectionManager()

    yield

    await app.state.db.dispose()
    await app.state.redis.close()
