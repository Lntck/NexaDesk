"""Add activity events table

Revision ID: d4a1f0b2c3e4
Revises: c7d41e92f0ab
Create Date: 2026-09-30 14:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d4a1f0b2c3e4"
down_revision: Union[str, Sequence[str], None] = "c7d41e92f0ab"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create the append-only activity history table."""
    op.create_table(
        "activity_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column(
            "type",
            sa.Enum(
                "PROJECT_CREATED",
                "PROJECT_UPDATED",
                "PROJECT_ARCHIVED",
                "PROJECT_RESTORED",
                "MEMBER_ADDED",
                "MEMBER_REMOVED",
                "MEMBER_ROLE_CHANGED",
                "TASK_CREATED",
                "TASK_UPDATED",
                "TASK_DELETED",
                "TASK_ASSIGNED",
                "TASK_UNASSIGNED",
                "TASK_STATUS_CHANGED",
                "TASK_MOVED",
                "RELATION_ADDED",
                "RELATION_REMOVED",
                "WATCHER_ADDED",
                "WATCHER_REMOVED",
                "COMMENT_CREATED",
                "COMMENT_UPDATED",
                "COMMENT_DELETED",
                "COMMENT_MENTIONED",
                "LABEL_ADDED",
                "LABEL_REMOVED",
                name="activity_event_type",
            ),
            nullable=False,
        ),
        sa.Column("project_id", sa.Integer(), nullable=True),
        sa.Column("task_id", sa.Integer(), nullable=True),
        sa.Column("actor_id", sa.Integer(), nullable=True),
        sa.Column("data", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            name=op.f("fk_activity_events_project_id_projects"),
        ),
        sa.ForeignKeyConstraint(
            ["task_id"], ["tasks.id"], name=op.f("fk_activity_events_task_id_tasks")
        ),
        sa.ForeignKeyConstraint(
            ["actor_id"], ["users.id"], name=op.f("fk_activity_events_actor_id_users")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_activity_events")),
    )
    op.create_index(
        op.f("ix_activity_events_project_id_created_at"),
        "activity_events",
        ["project_id", "created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_activity_events_task_id_created_at"),
        "activity_events",
        ["task_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    """Drop the activity history table."""
    op.drop_index(
        op.f("ix_activity_events_task_id_created_at"), table_name="activity_events"
    )
    op.drop_index(
        op.f("ix_activity_events_project_id_created_at"), table_name="activity_events"
    )
    op.drop_table("activity_events")
    sa.Enum(name="activity_event_type").drop(op.get_bind(), checkfirst=True)
