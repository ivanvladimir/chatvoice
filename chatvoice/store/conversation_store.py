import uuid as uuid_pkg
from datetime import UTC, datetime
from typing import Optional

from sqlalchemy import func, select, update

from ..core.db.database_sync import get_db_ctx
from ..models.conversation import (
    ConversationDocument,
    ConversationLog,
    ConversationTurn,
)


def _document_to_dict(doc: ConversationDocument) -> dict:
    """Must be called while `doc` is still attached to its session -- callers
    build this inside the `with get_db_ctx()` block that loaded it."""
    return {
        "uuid": str(doc.uuid),
        "title": doc.title,
        "kind": doc.kind,
        "content": doc.content,
        "tags": list(doc.tags),
        "created_at": doc.created_at.isoformat(),
        "updated_at": doc.updated_at.isoformat(),
    }


class ConversationLogStore:
    """
    Sync writer for conversation turns, called from the interpreter thread
    (cmd_say/cmd_listen) as they happen -- mirrors SqlAlchemyMemoryStore's
    sync-from-a-background-thread pattern.
    """

    def record_turn(
        self, conversation_log_id: Optional[int], role: str, text: str
    ) -> None:
        """No-ops if conversation_log_id is None (e.g. console transport, or a
        script with no resolvable Project row) so callers don't need to guard."""
        if not conversation_log_id:
            return

        with get_db_ctx() as db:
            current_max = db.execute(
                select(func.max(ConversationTurn.sequence)).where(
                    ConversationTurn.conversation_log_id == conversation_log_id
                )
            ).scalar()
            next_sequence = 0 if current_max is None else current_max + 1

            db.add(
                ConversationTurn(
                    conversation_log_id=conversation_log_id,
                    role=role,
                    text=text,
                    sequence=next_sequence,
                )
            )

    def close(self, conversation_log_id: Optional[int]) -> None:
        """Mark a conversation as finished. No-ops if conversation_log_id is None."""
        if not conversation_log_id:
            return

        with get_db_ctx() as db:
            db.execute(
                update(ConversationLog)
                .where(ConversationLog.id == conversation_log_id)
                .values(ended_at=datetime.now(UTC))
            )

    def add_conversation_tags(
        self, conversation_log_id: Optional[int], tags: list[str]
    ) -> None:
        """Adds whole-conversation tags (deduped). No-ops if conversation_log_id
        is None or tags is empty."""
        if not conversation_log_id or not tags:
            return

        with get_db_ctx() as db:
            current = db.execute(
                select(ConversationLog.tags).where(
                    ConversationLog.id == conversation_log_id
                )
            ).scalar()
            current = list(current or [])
            for tag in tags:
                if tag not in current:
                    current.append(tag)

            db.execute(
                update(ConversationLog)
                .where(ConversationLog.id == conversation_log_id)
                .values(tags=current)
            )

    def save_document(
        self,
        conversation_log_id: Optional[int],
        title: str,
        kind: str,
        content: str,
        tags: Optional[list[str]] = None,
    ) -> None:
        """Attaches a document (e.g. a cleanup-script analysis) to a
        conversation. No-ops if conversation_log_id is None."""
        if not conversation_log_id:
            return

        with get_db_ctx() as db:
            db.add(
                ConversationDocument(
                    conversation_log_id=conversation_log_id,
                    title=title,
                    kind=kind,
                    content=content,
                    tags=tags or [],
                    created_by_id=None,
                )
            )

    def list_documents(self, user_id: int, script_name: str) -> list[dict]:
        """All documents attached across every ConversationLog run of
        `script_name` by `user_id`, newest-updated first."""
        with get_db_ctx() as db:
            rows = (
                db.execute(
                    select(ConversationDocument)
                    .join(ConversationLog)
                    .where(
                        ConversationLog.user_id == user_id,
                        ConversationLog.script_name == script_name,
                    )
                    # id as a tiebreaker: SQLite's CURRENT_TIMESTAMP only has
                    # second resolution, so two saves in the same second tie
                    # on updated_at and would otherwise sort arbitrarily.
                    .order_by(
                        ConversationDocument.updated_at.desc(),
                        ConversationDocument.id.desc(),
                    )
                )
                .scalars()
                .all()
            )
            return [_document_to_dict(doc) for doc in rows]

    def get_document_by_uuid(
        self, user_id: int, document_uuid: uuid_pkg.UUID
    ) -> Optional[dict]:
        """Fetch a single document by its uuid, scoped to `user_id` so a
        script can't load another user's document by guessing an id."""
        with get_db_ctx() as db:
            doc = db.execute(
                select(ConversationDocument)
                .join(ConversationLog)
                .where(
                    ConversationDocument.uuid == document_uuid,
                    ConversationLog.user_id == user_id,
                )
            ).scalar_one_or_none()
            return _document_to_dict(doc) if doc else None

    def get_latest_document_by_title(
        self, user_id: int, script_name: str, title: str
    ) -> Optional[dict]:
        """Most recently updated document with this exact title, among all
        ConversationLog runs of `script_name` by `user_id`."""
        with get_db_ctx() as db:
            doc = db.execute(
                select(ConversationDocument)
                .join(ConversationLog)
                .where(
                    ConversationLog.user_id == user_id,
                    ConversationLog.script_name == script_name,
                    ConversationDocument.title == title,
                )
                .order_by(
                    ConversationDocument.updated_at.desc(),
                    ConversationDocument.id.desc(),
                )
                .limit(1)
            ).scalar_one_or_none()
            return _document_to_dict(doc) if doc else None
