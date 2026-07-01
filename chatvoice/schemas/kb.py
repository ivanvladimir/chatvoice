from datetime import datetime
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field

ProjectPath = Annotated[str, Field(max_length=64, examples=["/projects/my-kb"])]
Payload     = Annotated[dict[str, Any] | None, Field(default=None)]
OptionalStr = Annotated[str | None, Field(default=None, max_length=64)]
OptionalDt  = Annotated[datetime | None, Field(default=None)]

class KBBase(BaseModel):
    project_path: ProjectPath
    payload: Payload = None


class KBCreate(KBBase):
    user_id: Annotated[int, Field(gt=0)]

class KBUpdate(BaseModel):
    project_path: OptionalStr = None
    payload: Payload = None
    updated_at: OptionalDt = None

class KBUpdateInternal(KBUpdate):
    updated_at: datetime

class KBRead(KBBase):
    model_config = ConfigDict(from_attributes=True)

    id: Annotated[int, Field(gt=0)]
    user_id: Annotated[int, Field(gt=0)]
    created_at: datetime
    updated_at: OptionalDt = None
    deleted_at: OptionalDt = None
