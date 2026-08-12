from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from .user import UserBrief


class ConversationTurnRead(BaseModel):
    """A single say/listen turn, in order."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    role: Literal["user", "assistant"]
    text: str
    sequence: int
    created_at: datetime


class ConversationTurnCreateInternal(BaseModel):
    """Server-constructed. Not used through the async CRUD in practice --
    turns are written from the interpreter thread via the sync
    ConversationLogStore -- but FastCRUD's generic signature needs the slot."""

    conversation_log_id: int = Field(..., gt=0)
    role: Literal["user", "assistant"]
    text: str = Field(..., min_length=1)
    sequence: int = Field(..., ge=0)


class ConversationTurnUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ConversationTurnDelete(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ConversationLogCreateInternal(BaseModel):
    """Server-constructed: created once when a chat session starts."""

    user_id: int = Field(..., gt=0)
    project_id: int | None = Field(default=None)
    script_name: str = Field(..., min_length=1, max_length=500)
    session_id: str = Field(..., min_length=1, max_length=64)


class ConversationLogUpdate(BaseModel):
    """Used to close out a conversation once the session ends, or to edit its tags."""

    model_config = ConfigDict(extra="forbid")

    ended_at: datetime | None = Field(default=None)
    tags: list[str] | None = Field(default=None)


class ConversationLogUpdateInternal(ConversationLogUpdate):
    pass


class ConversationLogDelete(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ConversationLogListItem(BaseModel):
    """Compact schema for list views (my conversations / project conversations)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    uuid: UUID
    script_name: str
    started_at: datetime
    ended_at: datetime | None
    tags: list[str] = Field(default_factory=list)
    user: UserBrief


class ConversationLogRead(BaseModel):
    """Full schema for the transcript view: log metadata + ordered turns."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    uuid: UUID
    script_name: str
    started_at: datetime
    ended_at: datetime | None
    tags: list[str] = Field(default_factory=list)
    user: UserBrief
    turns: list[ConversationTurnRead] = Field(default_factory=list)


class ConversationDocumentRead(BaseModel):
    """A per-conversation analysis artifact."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    uuid: UUID
    conversation_log_id: int
    title: str
    kind: str
    content: str
    tags: list[str] = Field(default_factory=list)
    created_by_id: int | None
    created_at: datetime
    updated_at: datetime


class ConversationDocumentCreate(BaseModel):
    """User-facing input for manually attaching a document to a conversation."""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(..., min_length=1, max_length=200)
    kind: str = Field(..., min_length=1, max_length=100)
    content: str = Field(..., min_length=1)
    tags: list[str] = Field(default_factory=list)


class ConversationDocumentCreateInternal(ConversationDocumentCreate):
    conversation_log_id: int = Field(..., gt=0)
    created_by_id: int | None = Field(default=None)


class ConversationDocumentUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None)
    kind: str | None = Field(default=None)
    content: str | None = Field(default=None)
    tags: list[str] | None = Field(default=None)


class ConversationDocumentUpdateInternal(ConversationDocumentUpdate):
    pass


class ConversationDocumentDelete(BaseModel):
    model_config = ConfigDict(extra="forbid")
