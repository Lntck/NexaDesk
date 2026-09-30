from fastapi import APIRouter, Depends, Path, Request
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from app.auth.policy import RequireProjectRole
from app.auth.schemas import CurrentUser
from app.core import Settings, get_settings
from app.dependencies import (
    get_activity_crud,
    get_connection_manager,
    get_db_session,
    get_redis_client,
)
from app.enums import ProjectRole
from app.events.streams import ConnectionManager, project_event_stream
from app.protocols.activity import ActivityCRUDProtocol
from app.schemas.event import RealtimeEvent

router = APIRouter(tags=["Realtime"])


@router.get(
    "/projects/{project_id}/events",
    summary="Project realtime event stream (SSE)",
)
async def project_events(
    request: Request,
    current_user: CurrentUser = Depends(RequireProjectRole(ProjectRole.VIEWER)),
    session: AsyncSession = Depends(get_db_session),
    manager: ConnectionManager = Depends(get_connection_manager),
    activity_crud: ActivityCRUDProtocol = Depends(get_activity_crud),
    redis_client: Redis = Depends(get_redis_client),
    settings: Settings = Depends(get_settings),
    project_id: int = Path(...),
) -> EventSourceResponse:
    """Open a server-sent events stream of one project.

    The caller must be a project member. Events missed since the last seen
    id are replayed first when the client reconnects with the
    ``Last-Event-ID`` header, then live events follow, interleaved with
    heartbeat comments.

    Args:
        request: incoming request carrying the Last-Event-ID header.
        current_user: authenticated project member.
        session: database session used for replay lookups.
        manager: registry of open streams per client and project.
        activity_crud: activity history storage.
        redis_client: broker delivering live project events.
        settings: application settings with stream limits.
        project_id: project to stream.

    Returns:
        EventSourceResponse: stream of SSE frames.
    """
    replay: list[RealtimeEvent] = []
    last_event_id = request.headers.get("last-event-id")
    if last_event_id:
        rows = await activity_crud.list_events_after(
            session, project_id, last_event_id, settings.sse_replay_limit
        )
        replay = [RealtimeEvent.from_activity(row) for row in rows]

    # The stream outlives the request: release the pooled connection now.
    await session.close()

    stream = project_event_stream(
        manager=manager,
        redis_client=redis_client,
        project_id=project_id,
        user_id=current_user.id,
        replay=replay,
        heartbeat_s=settings.sse_heartbeat_s,
        idle_timeout_s=settings.sse_idle_timeout_s,
        max_queued_events=settings.sse_max_queued_events,
    )
    return EventSourceResponse(
        stream,
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
