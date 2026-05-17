"""SQLAlchemy PerformanceLog model — per-user topic performance tracking."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import String, DateTime, Integer, Float, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from pgvector.sqlalchemy import Vector

from ...database.postgres import Base

if TYPE_CHECKING:
    from .user import User


class PerformanceLog(Base):
    __tablename__ = "performance_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    topic: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    department: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    company: Mapped[str | None] = mapped_column(String(128), nullable=True)

    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    correct: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    success_rate: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    average_confidence: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    last_attempted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    user: Mapped["User"] = relationship("User", back_populates="performance_logs", lazy="noload")

    def __repr__(self) -> str:
        return f"<PerformanceLog user={self.user_id} topic={self.topic} rate={self.success_rate:.1%}>"


class TopicSkillVector(Base):
    """16-dimensional skill vector per department — used for personalization."""

    __tablename__ = "topic_skill_vectors"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    department: Mapped[str] = mapped_column(String(64), nullable=False)
    skill_vector: Mapped[list[float] | None] = mapped_column(Vector(16), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    def __repr__(self) -> str:
        return f"<TopicSkillVector user={self.user_id} dept={self.department}>"
