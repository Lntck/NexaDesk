from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base
from .user import User


class TaskWatcher(Base):
    """Subscription of one user to changes of one task."""

    __tablename__ = "task_watchers"

    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    user: Mapped[User] = relationship("User", lazy="selectin")

    __table_args__ = (
        UniqueConstraint("task_id", "user_id", name="uq_task_watchers_task_id_user_id"),
        Index(None, "user_id"),
    )
