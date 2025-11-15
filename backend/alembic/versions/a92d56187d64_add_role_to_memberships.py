"""Add role to memberships

Revision ID: a92d56187d64
Revises: 3d353c840601
Create Date: 2025-11-15 18:57:17.061814
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'a92d56187d64'
down_revision: Union[str, Sequence[str], None] = '3d353c840601'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

membership_role_enum = sa.Enum('owner', 'treasurer', 'member', name='membershiprole')

def upgrade():
    membership_role_enum.create(op.get_bind(), checkfirst=True)
    op.execute("ALTER TABLE memberships ALTER COLUMN role TYPE membershiprole USING role::membershiprole")

def downgrade():
    op.execute("ALTER TABLE memberships ALTER COLUMN role TYPE VARCHAR")
    membership_role_enum.drop(op.get_bind(), checkfirst=True)