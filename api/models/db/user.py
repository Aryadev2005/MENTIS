"""SQLAlchemy User model."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import String, DateTime, Boolean, Integer, Float, Text, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, ARRAY, JSONB
from pgvector.sqlalchemy import Vector

from ...database.postgres import Base

if TYPE_CHECKING:
    from .session import Session
    from .performance import PerformanceLog


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    clerk_id: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)

    college: Mapped[str | None] = mapped_column(String(255), nullable=True)
    graduation_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cgpa: Mapped[float | None] = mapped_column(Float, nullable=True)
    department: Mapped[str | None] = mapped_column(
        SAEnum("CSE", "ECE", "Mechanical", "Civil", "Chemical", "EEE", "Other", name="department_enum"),
        nullable=True,
    )
    current_role: Mapped[str | None] = mapped_column(
        SAEnum("fresher", "1-3yrs", "3-5yrs", "5+yrs", name="experience_enum"),
        nullable=True,
    )
    preferred_language: Mapped[str | None] = mapped_column(
        SAEnum("Python", "Java", "C++", "JavaScript", name="language_enum"),
        nullable=True,
    )

    plan: Mapped[str] = mapped_column(
        SAEnum("free", "student", "pro", "oa_pass", name="plan_enum"),
        default="free",
        nullable=False,
    )
    plan_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sessions_used: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    oa_solves_used: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    hardware_fingerprint: Mapped[str | None] = mapped_column(String(256), nullable=True)
    resume_parsed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    resume_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    skill_embedding: Mapped[list[float] | None] = mapped_column(Vector(3072), nullable=True)
    target_companies: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)

    calibration_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    onboarding_complete: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
    last_active_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    sessions: Mapped[list["Session"]] = relationship(
        "Session", back_populates="user", lazy="noload"
    )
    performance_logs: Mapped[list["PerformanceLog"]] = relationship(
        "PerformanceLog", back_populates="user", lazy="noload"
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email} plan={self.plan}>"
