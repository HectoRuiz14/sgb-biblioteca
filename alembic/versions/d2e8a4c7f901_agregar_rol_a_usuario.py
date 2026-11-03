"""agregar rol de autorización a usuario

Revision ID: d2e8a4c7f901
Revises: b7c1d2e3f4a5
Create Date: 2026-11-03 15:01:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d2e8a4c7f901"
down_revision: Union[str, Sequence[str], None] = "b7c1d2e3f4a5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "usuarios",
        sa.Column("rol", sa.String(length=20), nullable=False, server_default="USER"),
    )


def downgrade() -> None:
    op.drop_column("usuarios", "rol")
