from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator

from ..core.schemas import PersistentDeletion, TimestampSchema, UUIDSchema

from ..core.types import UserRole


class UserBase(BaseModel):
    name: Annotated[str, Field(min_length=2, max_length=30, examples=["User Userson"])]
    username: Annotated[
        str,
        Field(
            min_length=2, max_length=20, pattern=r"^[a-z0-9]+$", examples=["userson"]
        ),
    ]
    email: Annotated[EmailStr, Field(examples=["user.userson@example.com"])]
    role: Annotated[UserRole, Field(default=UserRole.user)]
    institution: Annotated[str | None, Field(default=None)]
    description: Annotated[str | None, Field(default=None)]
    is_verified: bool = False


class User(TimestampSchema, UserBase, UUIDSchema, PersistentDeletion):
    profile_image_url: Annotated[str | None, Field(default=None)]
    hashed_password: str
    tier_id: int | None = None


class UserRead(BaseModel):
    id: int

    name: Annotated[str, Field(min_length=2, max_length=30, examples=["User Userson"])]
    username: Annotated[
        str,
        Field(
            min_length=2, max_length=20, pattern=r"^[a-z0-9]+$", examples=["userson"]
        ),
    ]
    email: Annotated[EmailStr, Field(examples=["user.userson@example.com"])]
    institution: Annotated[str | None, Field(default=None)]
    description: Annotated[str | None, Field(default=None)]
    is_verified: bool
    role: UserRole

    profile_image_url: str | None

    tier_id: int | None

    model_config = ConfigDict(from_attributes=True)


class UserCreate(UserBase):
    model_config = ConfigDict(extra="forbid")
    password: Annotated[
        str,
        Field(
            pattern=r"^.{8,}|[0-9]+|[A-Z]+|[a-z]+|[^a-zA-Z0-9]+$",
            examples=["Str1ngst!"],
        ),
    ]

    @model_validator(mode="after")
    def force_user_role(self) -> "UserCreate":
        """Security: Always set role to 'user' on creation."""
        self.role = UserRole.user
        return self


class UserCreateInternal(UserBase):
    hashed_password: str | None = None
    profile_image_url: str | None = None


class UserUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Annotated[
        str | None,
        Field(min_length=2, max_length=30, examples=["User Userson"], default=None),
    ]

    username: Annotated[
        str | None,
        Field(
            min_length=2,
            max_length=20,
            pattern=r"^[a-z0-9]+$",
            examples=["userberg"],
            default=None,
        ),
    ]
    email: Annotated[
        EmailStr | None, Field(examples=["user.userberg@example.com"], default=None)
    ]
    role: UserRole = UserRole.user

    institution: Annotated[str | None, Field(default=None)]
    description: Annotated[str | None, Field(default=None)]
    password: Annotated[
        str | None,
        Field(
            pattern=r"^.{8,}|[0-9]+|[A-Z]+|[a-z]+|[^a-zA-Z0-9]+$",
            examples=["Str1ngst!"],
            default=None,
        ),
    ]

    profile_image_url: Annotated[
        str | None,
        Field(default=None),
    ]
    is_verified: Annotated[
        bool | None, Field(default=False, description="True if user is verified")
    ]


class UserUpdateInternal(UserUpdate):
    hashed_password: str
    updated_at: datetime


class UserRoleUpdate(BaseModel):
    """Used by admins to update a user's role."""

    model_config = ConfigDict(extra="forbid")

    role: UserRole


class UserTierUpdate(BaseModel):
    tier_id: int


class UserDelete(BaseModel):
    model_config = ConfigDict(extra="forbid")

    is_deleted: bool
    deleted_at: datetime


class UserRestoreDeleted(BaseModel):
    is_deleted: bool
