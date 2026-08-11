"""add conversation tags and document table

Revision ID: cf33459cc276
Revises: 71eec961a664
Create Date: 2026-08-11 12:32:36.064542

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "cf33459cc276"
down_revision: Union[str, Sequence[str], None] = "71eec961a664"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "conversation_log",
        sa.Column(
            "tags", sa.JSON(), server_default=sa.text("'[]'"), nullable=False
        ),
    )
    op.create_table(
        "conversation_document",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("conversation_log_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("kind", sa.String(length=100), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("tags", sa.JSON(), nullable=False),
        sa.Column("created_by_id", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["conversation_log_id"], ["conversation_log.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["created_by_id"], ["users.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_conversation_document_conversation_log_id"),
        "conversation_document",
        ["conversation_log_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_conversation_document_created_by_id"),
        "conversation_document",
        ["created_by_id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        op.f("ix_conversation_document_created_by_id"),
        table_name="conversation_document",
    )
    op.drop_index(
        op.f("ix_conversation_document_conversation_log_id"),
        table_name="conversation_document",
    )
    op.drop_table("conversation_document")
    op.drop_column("conversation_log", "tags")
