"""SQLAlchemy Question and Answer models for the question bank."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import String, DateTime, Integer, Float, Text, Boolean, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
from pgvector.sqlalchemy import Vector

from ...database.postgres import Base

if TYPE_CHECKING:
    from .session import Session


class Question(Base):
    __tablename__ = "questions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    session_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sessions.id", ondelete="SET NULL"), nullable=True, index=True
    )

    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    question_type: Mapped[str] = mapped_column(
        SAEnum(
            "behavioral", "technical", "hr", "coding", "aptitude",
            "mcq_cs", "mcq_ece", "mcq_mech", "mcq_civil", "mcq_chem",
            "debugging", "output_prediction",
            name="question_type_enum",
        ),
        nullable=False,
        index=True,
    )
    department: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    company: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    difficulty: Mapped[str | None] = mapped_column(
        SAEnum("easy", "medium", "hard", name="difficulty_enum"),
        nullable=True,
    )
    topic: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)

    answer_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence_score: Mapped[int | None] = mapped_column(Integer, nullable=True)

    question_embedding: Mapped[list[float] | None] = mapped_column(Vector(3072), nullable=True)
    answer_embedding: Mapped[list[float] | None] = mapped_column(Vector(3072), nullable=True)

    user_feedback: Mapped[str | None] = mapped_column(
        SAEnum("helpful", "not_helpful", "partially_helpful", name="feedback_enum"),
        nullable=True,
    )

    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    solve_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    options: Mapped[list | None] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    session: Mapped["Session | None"] = relationship(
        "Session", back_populates="questions", lazy="noload"
    )

    def __repr__(self) -> str:
        return f"<Question id={self.id} type={self.question_type} topic={self.topic}>"


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    category: Mapped[str] = mapped_column(
        SAEnum("mass_recruiter", "product", "core_engineering", "consulting_finance", name="company_category_enum"),
        nullable=False,
    )
    oa_format: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    typical_questions: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    student_reports: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    last_updated: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    def __repr__(self) -> str:
        return f"<Company name={self.name} category={self.category}>"
