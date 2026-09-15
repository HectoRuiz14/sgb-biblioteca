"""agregar campo activo a usuario

Revision ID: 3ad4c4226482
Revises: 3444886c7970
Create Date: 2026-09-15 11:24:27.157163

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3ad4c4226482'
down_revision: Union[str, Sequence[str], None] = '3444886c7970'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('usuarios', sa.Column('activo', sa.Boolean(), nullable=False, server_default=sa.true()))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('usuarios', 'activo')