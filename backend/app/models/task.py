from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.enums import Priority

from .base import Base
from .project import Project
from .task_status import TaskStatus
from .user import User


class Task(Base):
    """Unit of work inside a project, displayed as a card on the board."""

    __tablename__ = "tasks"

    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False)
    number: Mapped[int] = mapped_column(Integer, nullable=False)

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(String(10000), nullable=True)

    status_id: Mapped[int] = mapped_column(
        ForeignKey("task_statuses.id"), nullable=False
    )
    priority: Mapped[Priority] = mapped_column(
        Enum(Priority, name="priority"),
        default=Priority.MEDIUM,
        nullable=False,
    )

    creator_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    assignee_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    parent_task_id: Mapped[int | None] = mapped_column(
        ForeignKey("tasks.id"), nullable=True
    )

    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    estimated_hours: Mapped[Decimal | None] = mapped_column(
        Numeric(8, 2), nullable=True
    )

    # Optimistic concurrency token; every mutation increments it.
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    # Order of the card inside its board column.
    rank: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    project: Mapped[Project] = relationship("Project", lazy="selectin")
    status: Mapped[TaskStatus] = relationship("TaskStatus", lazy="selectin")
    creator: Mapped[User] = relationship(
        "User", foreign_keys=[creator_id], lazy="selectin"
    )
    assignee: Mapped[User | None] = relationship(
        "User", foreign_keys=[assignee_id], lazy="selectin"
    )

    __table_args__ = (
        UniqueConstraint("project_id", "number", name="uq_tasks_project_id_number"),
        Index(None, "status_id"),
        Index(None, "assignee_id"),
    )

    @property
    def key(self) -> str:
        """Return the public task key in the {project.key}-{number} format.

        Returns:
            str: human-facing task key, e.g. NEXA-17.
        """
        return f"{self.project.key}-{self.number}"
