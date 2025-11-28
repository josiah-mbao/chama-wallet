"""add first_name and last_name columns to users table

Revision ID: c23456789012
Revises: b12345678901
Create Date: 2025-11-28 17:13:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c23456789012"
down_revision: Union[str, None] = "b12345678901"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add first_name and last_name columns to users table."""
    # Add first_name column (required, with default for existing users)
    op.add_column("users", sa.Column("first_name", sa.String(100), nullable=False, server_default="User"))
    # Add last_name column (required, with default for existing users)  
    op.add_column("users", sa.Column("last_name", sa.String(100), nullable=False, server_default="Name"))


def downgrade() -> None:
    """Remove first_name and last_name columns from users table."""
    op.drop_column("users", "last_name")
    op.drop_column("users", "first_name")
