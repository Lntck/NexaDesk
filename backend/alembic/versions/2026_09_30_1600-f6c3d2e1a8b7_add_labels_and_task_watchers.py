"""Add labels and task watcher subscriptions

Revision ID: f6c3d2e1a8b7
Revises: e5b2a1c3d4f5
Create Date: 2026-09-30 16:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f6c3d2e1a8b7"
down_revision: Union[str, Sequence[str], None] = "e5b2a1c3d4f5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create the label, task label and task watcher tables."""
    op.create_table(
        "labels",
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.Column("color", sa.String(length=7), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.ForeignKeyConstraint(
            ["project_id"], ["projects.id"], name=op.f("fk_labels_project_id_projects")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_labels")),
    )
    op.create_index(
        op.f("ix_labels_project_id"), "labels", ["project_id"], unique=False
    )
    op.create_index(
        "uq_labels_project_id_lower_name",
        "labels",
        ["project_id", sa.literal_column("lower(name)")],
        unique=True,
    )
    op.create_table(
        "task_labels",
        sa.Column("task_id", sa.Integer(), nullable=False),
        sa.Column("label_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.ForeignKeyConstraint(
            ["task_id"], ["tasks.id"], name=op.f("fk_task_labels_task_id_tasks")
        ),
        sa.ForeignKeyConstraint(
            ["label_id"], ["labels.id"], name=op.f("fk_task_labels_label_id_labels")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_task_labels")),
        sa.UniqueConstraint(
            "task_id", "label_id", name="uq_task_labels_task_id_label_id"
        ),
    )
    op.create_index(
        op.f("ix_task_labels_label_id"), "task_labels", ["label_id"], unique=False
    )
    op.create_table(
        "task_watchers",
        sa.Column("task_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.ForeignKeyConstraint(
            ["task_id"], ["tasks.id"], name=op.f("fk_task_watchers_task_id_tasks")
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_task_watchers_user_id_users")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_task_watchers")),
        sa.UniqueConstraint(
            "task_id", "user_id", name="uq_task_watchers_task_id_user_id"
        ),
    )
    op.create_index(
        op.f("ix_task_watchers_user_id"), "task_watchers", ["user_id"], unique=False
    )


def downgrade() -> None:
    """Drop the label, task label and task watcher tables."""
    op.drop_index(op.f("ix_task_watchers_user_id"), table_name="task_watchers")
    op.drop_table("task_watchers")
    op.drop_index(op.f("ix_task_labels_label_id"), table_name="task_labels")
    op.drop_table("task_labels")
    op.drop_index("uq_labels_project_id_lower_name", table_name="labels")
    op.drop_index(op.f("ix_labels_project_id"), table_name="labels")
    op.drop_table("labels")
