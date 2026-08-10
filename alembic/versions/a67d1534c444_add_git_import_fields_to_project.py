"""add git import fields to project

Revision ID: a67d1534c444
Revises: 0f9db94ab7d6
Create Date: 2026-08-08 17:39:05.928473

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a67d1534c444"
down_revision: Union[str, Sequence[str], None] = "0f9db94ab7d6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "project", sa.Column("source_url", sa.String(length=1000), nullable=True)
    )
    op.add_column(
        "project",
        sa.Column(
            "import_status",
            sa.String(length=20),
            nullable=False,
            server_default="ready",
        ),
    )
    op.add_column(
        "project", sa.Column("import_error", sa.String(length=1000), nullable=True)
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("project", "import_error")
    op.drop_column("project", "import_status")
    op.drop_column("project", "source_url")
