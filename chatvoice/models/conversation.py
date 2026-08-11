import uuid as uuid_pkg
from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from uuid6 import uuid7

from ..core.db import Base


class ConversationLog(Base):
    """One run of a conversation script (roughly: one chat session)."""

    __tablename__ = "conversation_log"

    id: Mapped[int] = mapped_column(autoincrement=True, primary_key=True, init=False)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, kw_only=True
    )
    # Nullable: not every runnable script (e.g. the built-in hello_world demo)
    # has a matching Project row.
    project_id: Mapped[int | None] = mapped_column(
        ForeignKey("project.id", ondelete="CASCADE"),
        index=True,
        default=None,
        kw_only=True,
    )
    script_name: Mapped[str] = mapped_column(String(500), kw_only=True)
    # The ChatSession.session_id that produced this log, for correlating with
    # a still-live session. Not unique: a reconnect creates a new session_id
    # for the same logical conversation, hence a new log row.
    session_id: Mapped[str] = mapped_column(String(64), index=True, kw_only=True)

    uuid: Mapped[uuid_pkg.UUID] = mapped_column(
        UUID(as_uuid=True), default_factory=uuid7, unique=True, kw_only=True
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), init=False
    )
    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None, kw_only=True
    )
    # Whole-conversation labels (distinct from the DSL `tag` command, which
    # tags turns/segments *within* a running conversation).
    tags: Mapped[list[str]] = mapped_column(
        JSON, default_factory=list, server_default=text("'[]'"), kw_only=True
    )

    user: Mapped["User"] = relationship(
        "User", back_populates="conversation_logs", init=False
    )
    project: Mapped["Project | None"] = relationship(
        "Project", back_populates="conversation_logs", init=False
    )
    turns: Mapped[list["ConversationTurn"]] = relationship(
        "ConversationTurn",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="ConversationTurn.sequence",
        default_factory=list,
    )
    documents: Mapped[list["ConversationDocument"]] = relationship(
        "ConversationDocument",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="ConversationDocument.created_at",
        default_factory=list,
    )

    def __repr__(self) -> str:
        return (
            f"<ConversationLog id={self.id!r} script_name={self.script_name!r} "
            f"user_id={self.user_id!r}>"
        )


class ConversationTurn(Base):
    """A single say/listen turn within a ConversationLog, in order."""

    __tablename__ = "conversation_turn"

    id: Mapped[int] = mapped_column(autoincrement=True, primary_key=True, init=False)

    conversation_log_id: Mapped[int] = mapped_column(
        ForeignKey("conversation_log.id", ondelete="CASCADE"),
        index=True,
        kw_only=True,
    )
    # "user" | "assistant"
    role: Mapped[str] = mapped_column(String(20), kw_only=True)
    text: Mapped[str] = mapped_column(Text, kw_only=True)
    # 0-indexed position within the conversation, for stable ordering.
    sequence: Mapped[int] = mapped_column(Integer, kw_only=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), init=False
    )

    conversation: Mapped["ConversationLog"] = relationship(
        "ConversationLog", back_populates="turns", init=False
    )

    def __repr__(self) -> str:
        return f"<ConversationTurn id={self.id!r} role={self.role!r} sequence={self.sequence!r}>"


class ConversationDocument(Base):
    """A per-conversation analysis artifact (e.g. sentiment, summary, quality)."""

    __tablename__ = "conversation_document"

    id: Mapped[int] = mapped_column(autoincrement=True, primary_key=True, init=False)

    conversation_log_id: Mapped[int] = mapped_column(
        ForeignKey("conversation_log.id", ondelete="CASCADE"),
        index=True,
        kw_only=True,
    )
    title: Mapped[str] = mapped_column(String(200), kw_only=True)
    # Free-text label (e.g. "sentimiento", "resumen") -- not an enum, so new
    # kinds of analysis can be added without a migration.
    kind: Mapped[str] = mapped_column(String(100), kw_only=True)
    content: Mapped[str] = mapped_column(Text, kw_only=True)
    tags: Mapped[list[str]] = mapped_column(JSON, default_factory=list, kw_only=True)

    created_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        index=True,
        default=None,
        kw_only=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), init=False
    )

    conversation: Mapped["ConversationLog"] = relationship(
        "ConversationLog", back_populates="documents", init=False
    )

    def __repr__(self) -> str:
        return f"<ConversationDocument id={self.id!r} title={self.title!r} kind={self.kind!r}>"
