"""add is_active and role columns to users table

Revision ID: b12345678901
Revises: a92d56187d64
Create Date: 2025-11-28 16:55:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b12345678901"
down_revision: Union[str, None] = "a92d56187d64"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add is_active and role columns to users table."""
    # Create the enum type first
    userrole_enum = sa.Enum("owner", "treasurer", "member", name="userrole")
    userrole_enum.create(op.get_bind(), checkfirst=True)

    # Add is_active column with default value true
    op.add_column("users", sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")))
    # Add role column with default value "member"
    op.add_column("users", sa.Column("role", userrole_enum, nullable=False, server_default="member"))


def downgrade() -> None:
    """Remove is_active and role columns from users table."""
    op.drop_column("users", "role")
    op.drop_column("users", "is_active")
