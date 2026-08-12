"""add uuid and updated_at to conversation_document

Revision ID: 5c4216b73e26
Revises: cf33459cc276
Create Date: 2026-08-12 15:44:59.576895

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "5c4216b73e26"
down_revision: Union[str, Sequence[str], None] = "cf33459cc276"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("conversation_document", sa.Column("uuid", sa.UUID(), nullable=False))
    op.add_column(
        "conversation_document",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
    )
    # batch_alter_table: SQLite can't ALTER a table to add a unique
    # constraint in place; this recreates the table under the hood.
    with op.batch_alter_table("conversation_document") as batch_op:
        batch_op.create_unique_constraint("uq_conversation_document_uuid", ["uuid"])


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("conversation_document") as batch_op:
        batch_op.drop_constraint("uq_conversation_document_uuid", type_="unique")
    op.drop_column("conversation_document", "updated_at")
    op.drop_column("conversation_document", "uuid")
