from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base
from .label import Label


class TaskLabel(Base):
    """Attachment of one label to one task."""

    __tablename__ = "task_labels"

    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id"), nullable=False)
    label_id: Mapped[int] = mapped_column(ForeignKey("labels.id"), nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    label: Mapped[Label] = relationship("Label", lazy="selectin")

    __table_args__ = (
        UniqueConstraint("task_id", "label_id", name="uq_task_labels_task_id_label_id"),
        Index(None, "label_id"),
    )
