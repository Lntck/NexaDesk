from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base

# name, key, color, position of the columns created with every project.
DEFAULT_TASK_STATUSES: tuple[tuple[str, str, str, int], ...] = (
    ("TODO", "TODO", "#8993A4", 1),
    ("In Progress", "IN_PROGRESS", "#0C66E4", 2),
    ("Review", "REVIEW", "#F5CD47", 3),
    ("Done", "DONE", "#4BCE97", 4),
)


class TaskStatus(Base):
    """Board column of one project; tasks reference it as their status."""

    __tablename__ = "task_statuses"

    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    key: Mapped[str] = mapped_column(String(30), nullable=False)
    color: Mapped[str] = mapped_column(String(7), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)

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

    __table_args__ = (
        UniqueConstraint("project_id", "key", name="uq_task_statuses_project_id_key"),
    )
