from typing import AsyncGenerator

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.events import get_event_publisher
from app.events import drain_events


async def get_db_session(
    request: Request,
) -> AsyncGenerator[AsyncSession, None]:
    """Provide one database session per request.

    The underlying session is committed when the request finishes; queued
    domain events are published strictly after that commit and dropped on
    rollback.

    Args:
        request: incoming request carrying the application state.

    Yields:
        AsyncSession: session bound to the request transaction.
    """
    db = request.app.state.db
    publisher = get_event_publisher()

    async for session in db.session_getter():
        yield session

    for event in drain_events(session):
        await publisher.publish(event)
