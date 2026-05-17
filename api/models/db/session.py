"""SQLAlchemy Session model — interview/OA sessions."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import String, DateTime, Integer, Float, Text, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB

from ...database.postgres import Base

if TYPE_CHECKING:
    from .user import User
    from .question import Question


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    mode: Mapped[str] = mapped_column(
        SAEnum("interview", "oa", "mock", name="session_mode_enum"),
        nullable=False,
    )
    company: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    role: Mapped[str | None] = mapped_column(String(256), nullable=True)
    department: Mapped[str | None] = mapped_column(String(64), nullable=True)
    group_code: Mapped[str | None] = mapped_column(String(6), nullable=True, index=True)

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)

    qa_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    average_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    topics_encountered: Mapped[list | None] = mapped_column(JSONB, nullable=True)

    debrief: Mapped[str | None] = mapped_column(Text, nullable=True)
    debrief_generated: Mapped[bool] = mapped_column(
        __import__("sqlalchemy").Boolean, default=False, nullable=False
    )

    metadata_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="sessions", lazy="noload")
    questions: Mapped[list["Question"]] = relationship(
        "Question", back_populates="session", lazy="noload", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Session id={self.id} mode={self.mode} company={self.company}>"
