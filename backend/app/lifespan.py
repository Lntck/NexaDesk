import asyncio
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI

from app.core import get_settings
from app.core.metrics import set_app_info
from app.core.metrics_server import MetricsApp, MetricsServer, OverdueTasksSnapshot
from app.db import DatabaseClient, RedisClient
from app.events.publisher import DatabaseActorLookup, RedisPublisher
from app.events.streams import ConnectionManager


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Build shared infrastructure on startup and dispose it on shutdown.

    The database client, the Redis client, the realtime event publisher
    and the SSE connection registry live on app.state for the whole
    process lifetime. When metrics are enabled, the dedicated metrics
    server and the gauge snapshot task are started alongside them.

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

    set_app_info(settings.service_name, settings.service_version)

    metrics_server = None
    snapshot_task: asyncio.Task | None = None
    if settings.metrics_enabled:
        metrics_server = MetricsServer(
            MetricsApp(), settings.metrics_host, settings.metrics_port
        )
        await metrics_server.start()
        snapshot_task = asyncio.create_task(
            OverdueTasksSnapshot(app.state.db).run(), name="metrics-snapshots"
        )

    yield

    if snapshot_task is not None:
        snapshot_task.cancel()
        with suppress(asyncio.CancelledError):
            await snapshot_task
    if metrics_server is not None:
        await metrics_server.stop()

    await app.state.db.dispose()
    await app.state.redis.close()
