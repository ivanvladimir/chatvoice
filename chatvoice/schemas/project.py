from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator
from enum import Enum

class ProjectPermission(str, Enum):
    VIEW = "view"
    EDIT = "edit"

# =============================================================================
# Project Member Schemas
# =============================================================================

class ProjectMemberBase(BaseModel):
    """Base schema with shared fields."""
    permission: Literal["view", "edit"] = Field(
        ...,
        description="Permission level: 'view' or 'edit'"
    )


class ProjectMemberCreate(ProjectMemberBase):
    """Schema for adding a member to a project."""
    user_id: int = Field(..., gt=0, description="ID of the user to add")


class ProjectMemberUpdate(BaseModel):
    """Schema for updating a member's permission."""
    permission: Literal["view", "edit"] = Field(
        ...,
        description="New permission level: 'view' or 'edit'"
    )


class ProjectMemberRead(ProjectMemberBase):
    """Schema for returning project member data."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    user_id: int


class ProjectMemberReadWithUser(ProjectMemberRead):
    """Extended schema with nested user info."""
    # Import from your user schemas
    # from .user import UserBrief
    # user: UserBrief
    pass


# =============================================================================
# Project Schemas
# =============================================================================

class ProjectBase(BaseModel):
    """Base schema with shared fields."""
    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Project name"
    )
    description: str | None = Field(
        default=None,
        description="Optional project description"
    )


class ProjectCreate(ProjectBase):
    """Schema for creating a new project."""
    directory_path: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Root directory path for the project"
    )
    
    # Note: owner_id is typically set from authenticated user, not request body
    # Include only if you want to allow specifying owner explicitly
    # owner_id: int | None = None


class ProjectUpdate(BaseModel):
    """Schema for updating a project. All fields are optional."""
    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=100
    )
    directory_path: str | None = Field(
        default=None,
        min_length=1,
        max_length=500
    )
    description: str | None = Field(default=None)
    is_active: bool | None = Field(default=None)


class ProjectUpdateInternal(ProjectUpdate):
    udated_at: datetime

class ProjectRead(BaseModel):
    """Schema for returning project data (without relationships)."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    directory_path: str
    is_active: bool
    description: str | None
    owner_id: int
    uuid: UUID
    created_at: datetime
    updated_at: datetime | None
    deleted_at: datetime | None
    is_deleted: bool


class ProjectListItem(BaseModel):
    """Compact schema for list views."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    directory_path: str
    is_active: bool
    uuid: UUID
    created_at: datetime
    
    # Optional: include owner brief if needed
    # owner: "UserBrief"


class ProjectDetail(ProjectRead):
    """Full project schema with relationships."""
    model_config = ConfigDict(from_attributes=True)

    # Import from your user schemas
    # from .user import UserBrief
    # owner: UserBrief
    member_links: list[ProjectMemberRead] = Field(default_factory=list)


class ProjectDetailWithUsers(ProjectDetail):
    """Full project schema with member user details."""
    member_links: list[ProjectMemberReadWithUser] = Field(default_factory=list)



