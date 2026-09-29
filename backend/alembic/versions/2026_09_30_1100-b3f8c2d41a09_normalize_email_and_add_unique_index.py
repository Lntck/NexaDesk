"""Normalize email and add case-insensitive uniqueness

Revision ID: b3f8c2d41a09
Revises: a22c501118b2
Create Date: 2026-09-30 11:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b3f8c2d41a09"
down_revision: Union[str, Sequence[str], None] = "a22c501118b2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Lowercase stored emails and enforce uniqueness case-insensitively."""
    op.drop_constraint(op.f("uq_users_email"), "users", type_="unique")
    op.execute(sa.text("UPDATE users SET email = lower(email)"))
    op.create_index(
        op.f("ix_users_email"),
        "users",
        [sa.literal_column("lower(email)")],
        unique=True,
    )


def downgrade() -> None:
    """Restore the plain unique email constraint."""
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.create_unique_constraint(op.f("uq_users_email"), "users", ["email"])