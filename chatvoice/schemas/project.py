from datetime import datetime
from enum import Enum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from ..models.user import User
from .user import UserBrief


class ProjectPermission(str, Enum):
    VIEW = "view"
    EDIT = "edit"


# =============================================================================
# Project Member Schemas
# =============================================================================


class ProjectMemberBase(BaseModel):
    """Base schema with shared fields."""

    permission: Literal["view", "edit"] = Field(
        ..., description="Permission level: 'view' or 'edit'"
    )


class ProjectMemberCreate(ProjectMemberBase):
    """Schema for adding a member to a project."""

    identifier: str = Field(
        ..., min_length=1, description="Username or email of the user to add"
    )


class ProjectMemberUpdate(BaseModel):
    """Schema for updating a member's permission."""

    permission: Literal["view", "edit"] = Field(
        ..., description="New permission level: 'view' or 'edit'"
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

    name: str = Field(..., min_length=1, max_length=100, description="Project name")
    description: str | None = Field(
        default=None, description="Optional project description"
    )


class ProjectCreate(ProjectBase):
    """Schema for creating a new project."""

    project_name: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Project name",
    )


class ProjectCreateInternal(ProjectCreate):
    """Internal schema with owner_id added server-side."""

    owner_id: int = Field(
        ..., gt=0, description="ID of the project owner (set server-side)"
    )


class ProjectImportGit(BaseModel):
    """Schema for importing a project by cloning a GitHub/GitLab repo."""

    name: str = Field(..., min_length=1, max_length=100, description="Project name")
    project_name: str | None = Field(
        default=None,
        max_length=500,
        description="Project key. Derived from the repo name if left blank.",
    )
    git_url: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="HTTPS URL of the GitHub or GitLab repository to clone",
    )


class ProjectImportInternal(ProjectCreateInternal):
    """Internal schema for creating a project row while a git import is running."""

    source_url: str = Field(..., max_length=1000)
    import_status: str = Field(default="importing", max_length=20)


class ProjectUpdate(BaseModel):
    """Schema for updating a project. All fields are optional."""

    name: str | None = Field(default=None, min_length=1, max_length=100)
    directory_path: str | None = Field(default=None, min_length=1, max_length=500)
    description: str | None = Field(default=None)
    is_active: bool | None = Field(default=None)
    import_status: str | None = Field(default=None, max_length=20)
    import_error: str | None = Field(default=None, max_length=1000)


class ProjectUpdateInternal(ProjectUpdate):
    udated_at: datetime = None


class ProjectRead(BaseModel):
    """Schema for returning project data (without relationships)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    project_name: str
    is_active: bool
    description: str | None
    owner_id: int
    owner: User
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
    project_name: str
    is_active: bool
    uuid: UUID
    created_at: datetime
    source_url: str | None = None
    import_status: str = "ready"
    import_error: str | None = None

    owner: UserBrief


class ProjectDetail(ProjectRead):
    """Full project schema with relationships."""

    model_config = ConfigDict(from_attributes=True)

    # Import from your user schemas
    owner: UserBrief
    member_links: list[ProjectMemberRead] = Field(default_factory=list)


class ProjectDetailWithUsers(ProjectDetail):
    """Full project schema with member user details."""

    member_links: list[ProjectMemberReadWithUser] = Field(default_factory=list)


class ProjectDelete(BaseModel):
    model_config = ConfigDict(extra="forbid")

    is_deleted: bool
    deleted_at: datetime
