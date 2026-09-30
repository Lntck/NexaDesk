from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.enums import ActivityEventType

from .base import Base
from .project import Project
from .task import Task
from .user import User


class ActivityEvent(Base):
    """Immutable history entry of an important domain change."""

    __tablename__ = "activity_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)  # type: ignore[assignment]
    type: Mapped[ActivityEventType] = mapped_column(
        Enum(ActivityEventType, name="activity_event_type"),
        nullable=False,
    )

    project_id: Mapped[int | None] = mapped_column(
        ForeignKey("projects.id"), nullable=True
    )
    task_id: Mapped[int | None] = mapped_column(ForeignKey("tasks.id"), nullable=True)
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    project: Mapped[Project | None] = relationship("Project", lazy="selectin")
    task: Mapped[Task | None] = relationship("Task", lazy="selectin")
    actor: Mapped[User | None] = relationship("User", lazy="selectin")

    __table_args__ = (
        Index(None, "project_id", "created_at"),
        Index(None, "task_id", "created_at"),
    )
