from enum import Enum
from pydantic import BaseModel

class UserRole(str, Enum):
    user = "user"
    editor = "editor"
    admin = "admin"

class UserResponse(BaseModel):
    """Current user info response."""

    id: int
    username: str
    name: str
    email: str
    is_verified: bool
    role: UserRole


