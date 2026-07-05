import uuid as uuid_pkg
from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from uuid6 import uuid7

from core.db import Base

class ProjectMember(Base):
    """Association table to handle Project <-> User with specific permissions."""
    __tablename__ = "project_member"

    id: Mapped[int] = mapped_column(autoincrement=True, primary_key=True, init=False)
    
    project_id: Mapped[int] = mapped_column(ForeignKey("project.id"), init=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), init=False)
    
    permission: Mapped[str] = mapped_column(String(10)) # "view" or "edit"

    # Relationships
    project: Mapped["Project"] = relationship(back_populates="member_links")
    user: Mapped["User"] = relationship(back_populates="project_memberships")


class Project(Base):
    """The main Project model."""
    __tablename__ = "project"

    id: Mapped[int] = mapped_column(autoincrement=True, primary_key=True, init=False)
    name: Mapped[str] = mapped_column(String(100))
    directory_path: Mapped[str] = mapped_column(String(500), unique=True, index=True)

    # The root directory path for this project (e.g., "s3://my-bucket/projects/uuid/" or "/var/www/projects/uuid/")
    is_active: Mapped[bool] = mapped_column(default=True)
    description: Mapped[str | None] = mapped_column(String, default=None, nullable=True)

    # The creator/owner of the project
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, init=False)
    owner: Mapped["User"] = relationship("User", back_populates="owned_projects", init=False)

    uuid: Mapped[uuid_pkg.UUID] = mapped_column(UUID(as_uuid=True), default_factory=uuid7, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default_factory=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    is_deleted: Mapped[bool] = mapped_column(default=False, index=True)

    # Relationships
    member_links: Mapped[list["ProjectMember"]] = relationship(
        "ProjectMember", 
        back_populates="project", 
        cascade="all, delete-orphan", 
        default_factory=list
    )

    def __repr__(self) -> str:
        return (
            f"<project id={self.id!r} name={self.name!r} dir={self.directory_path!r}>"
        )
