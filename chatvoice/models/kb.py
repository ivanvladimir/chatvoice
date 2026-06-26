from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, String, JSON, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.db import Base

class KB(Base):
    __tablename__ = "kb"

    id: Mapped[int] = mapped_column(autoincrement=True, primary_key=True, init=False)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("user.id", ondelete="CASCADE"), nullable=False
    )
    project_path: Mapped[str] = mapped_column(
        String(64), nullable=False, default=""
    )
    payload: Mapped[dict] = mapped_column(JSON, default=None, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default_factory=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)

    # Relationships — always declare AFTER columns
    user: Mapped["User"] = relationship(
        "User", back_populates="kbs", default=None
    )

    def __repr__(self) -> str:
        return (
            f"<kb id={self.id!r} user_id={self.user_id!r} project_path={self.project_path!r}>"
        )
