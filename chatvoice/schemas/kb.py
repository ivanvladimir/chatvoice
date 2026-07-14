import json
from datetime import datetime
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

ProjectPath = Annotated[str, Field(max_length=64, examples=["/projects/my-kb"])]
Payload     = Annotated[dict[str, Any] | None, Field(default=None)]
OptionalStr = Annotated[str | None, Field(default=None, max_length=64)]
OptionalDt  = Annotated[datetime | None, Field(default=None)]

class KBBase(BaseModel):
    project_path: ProjectPath
    payload: Payload = None

    @field_validator("payload", mode="before")
    @classmethod
    def parse_payload(cls, v: Any) -> dict[str, Any] | None:
        if v is None:
            return None
        if isinstance(v, dict):
            return v
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON string for payload: {e}")
        raise ValueError(f"payload must be a dict or JSON string, got {type(v).__name__}")

class KBCreate(KBBase):
    user_id: Annotated[int, Field(gt=0)]

class KBUpdate(BaseModel):
    project_path: OptionalStr = None
    payload: Payload = None

    @field_validator("payload", mode="before")
    @classmethod
    def parse_payload(cls, v: Any) -> dict[str, Any] | None:
        if v is None:
            return None
        if isinstance(v, dict):
            return v
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON string for payload: {e}")
        raise ValueError(f"payload must be a dict or JSON string, got {type(v).__name__}")

class KBUpdateInternal(KBUpdate):
    updated_at: datetime

class KBRead(KBBase):
    model_config = ConfigDict(from_attributes=True)

    id: Annotated[int, Field(gt=0)]
    user_id: Annotated[int, Field(gt=0)]
    created_at: datetime
    updated_at: OptionalDt = None
    deleted_at: OptionalDt = None

class KBDelete(BaseModel):
    model_config = ConfigDict(extra="forbid")

    is_deleted: bool
    deleted_at: datetime


class KBRestoreDeleted(BaseModel):
    is_deleted: bool
