from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, String, JSON, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.db import Base


class KB(Base):
    __tablename__ = "kb"
    id: Mapped[int] = mapped_column(autoincrement=True, primary_key=True, init=False)
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        kw_only=True,
    )
    project_path: Mapped[str] = mapped_column(
        String(64), nullable=False, default="", kw_only=True
    )
    payload: Mapped[dict] = mapped_column(
        JSON, default=None, nullable=True, kw_only=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default_factory=lambda: datetime.now(UTC), kw_only=True
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None, kw_only=True
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None, kw_only=True
    )
    user: Mapped["User"] = relationship(
        "User", back_populates="kbs", default=None, kw_only=True, init=False
    )
    is_deleted: Mapped[bool] = mapped_column(default=False, index=True)

    def __repr__(self) -> str:
        return f"<kb id={self.id!r} user_id={self.user_id!r} project_path={self.project_path!r} is_deleted={self.is_deleted}>"
