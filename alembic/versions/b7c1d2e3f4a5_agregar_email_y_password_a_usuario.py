"""agregar email y password_hash a usuario

Revision ID: b7c1d2e3f4a5
Revises: 3ad4c4226482
Create Date: 2026-10-20 14:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b7c1d2e3f4a5'
down_revision: Union[str, Sequence[str], None] = '3ad4c4226482'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('usuarios', sa.Column('email', sa.String(length=120), nullable=True))
    op.add_column('usuarios', sa.Column('password_hash', sa.String(length=255), nullable=True))
    op.create_index(op.f('ix_usuarios_email'), 'usuarios', ['email'], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_usuarios_email'), table_name='usuarios')
    op.drop_column('usuarios', 'password_hash')
    op.drop_column('usuarios', 'email')
