from typing import List, Union
from datetime import datetime
from pydantic import BaseModel

class UserBase(BaseModel):
    identifier: str

class UserCreate(UserBase):
    data: str

class User(UserBase):
    id: int
    is_active: bool
    time_created: datetime
    time_updated: datetime

    class Config:
        orm_mode = True
