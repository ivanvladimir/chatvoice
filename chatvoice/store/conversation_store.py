from datetime import UTC, datetime
from typing import Optional

from sqlalchemy import func, select, update

from ..core.db.database_sync import get_db_ctx
from ..models.conversation import ConversationLog, ConversationTurn


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
