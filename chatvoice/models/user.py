from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from uuid6 import uuid7

from ..core.db import Base
from ..core.types import UserRole
from .project import Project, ProjectMember


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(autoincrement=True, primary_key=True, init=False)

    name: Mapped[str] = mapped_column(String(30))
    username: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    profile_image_url: Mapped[str | None] = mapped_column(String, nullable=True)
    institution: Mapped[str | None] = mapped_column(String, nullable=True)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    uuid: Mapped[uuid7] = mapped_column(
        UUID(as_uuid=True), default_factory=uuid7, unique=True
    )

    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, native_enum=False), default=UserRole.user, index=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), init=False
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        init=False,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, init=False
    )
    is_deleted: Mapped[bool] = mapped_column(default=False, index=True)
    is_verified: Mapped[bool] = mapped_column(
        default=False, index=True
    )  # Added index, often used for filtering

    tier_id: Mapped[int | None] = mapped_column(
        ForeignKey("tier.id"), index=True, default=None, init=False
    )

    kbs: Mapped[list["KB"]] = relationship(
        "KB",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
        default_factory=list,
    )
    owned_projects: Mapped[list["Project"]] = relationship(
        "Project",
        back_populates="owner",
        lazy="selectin",
        default_factory=list,
        # Note: Consider if you want cascade="all, delete-orphan" here too
    )
    project_memberships: Mapped[list["ProjectMember"]] = relationship(
        "ProjectMember", back_populates="user", lazy="selectin", default_factory=list
    )

    def __repr__(self) -> str:
        return f"<User id={self.id!r} username={self.username!r} email={self.email!r}>"
