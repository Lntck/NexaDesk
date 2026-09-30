from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.enums import NotificationType

from .base import Base
from .user import User


class Notification(Base):
    """User-scoped notice about a domain change the user cares about."""

    __tablename__ = "notifications"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    project_id: Mapped[int | None] = mapped_column(
        ForeignKey("projects.id"), nullable=True
    )
    task_id: Mapped[int | None] = mapped_column(ForeignKey("tasks.id"), nullable=True)
    comment_id: Mapped[int | None] = mapped_column(
        ForeignKey("comments.id"), nullable=True
    )

    activity_event_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("activity_events.id"), nullable=False
    )
    type: Mapped[NotificationType] = mapped_column(
        Enum(NotificationType, name="notification_type"),
        nullable=False,
    )

    # Snapshot of the source (project key, task key and title) plus the
    # event specific attributes, so the notice stays readable after the
    # source task is renamed or soft-deleted.
    data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    read_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    actor: Mapped[User | None] = relationship(
        "User", foreign_keys=[actor_id], lazy="selectin"
    )

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "activity_event_id",
            name="uq_notifications_user_id_activity_event_id",
        ),
        Index(None, "user_id", "created_at"),
        Index(None, "user_id", "read_at"),
    )
