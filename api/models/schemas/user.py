"""Pydantic v2 schemas for user-related request/response."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator


class UserCreate(BaseModel):
    clerk_id: str = Field(..., min_length=1, max_length=128)
    email: EmailStr
    name: str = Field(..., min_length=1, max_length=128)
    phone: str | None = Field(None, pattern=r"^\+?[0-9]{10,15}$")


class OnboardingStep1(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    email: EmailStr
    phone: str | None = Field(None, pattern=r"^\+?[0-9]{10,15}$")


class OnboardingStep2(BaseModel):
    college: str = Field(..., min_length=2, max_length=255)
    graduation_year: int = Field(..., ge=2000, le=2035)
    cgpa: float = Field(..., ge=0.0, le=10.0)


class OnboardingStep3(BaseModel):
    department: Literal["CSE", "ECE", "Mechanical", "Civil", "Chemical", "EEE", "Other"]


class OnboardingStep5(BaseModel):
    target_companies: list[str] = Field(..., min_length=1, max_length=20)


class OnboardingStep6(BaseModel):
    current_role: Literal["fresher", "1-3yrs", "3-5yrs", "5+yrs"]


class OnboardingStep7(BaseModel):
    preferred_language: Literal["Python", "Java", "C++", "JavaScript"]


class CalibrationAnswer(BaseModel):
    question_id: str
    answer: str
    time_taken_seconds: int = Field(..., ge=0)


class OnboardingStep8(BaseModel):
    answers: list[CalibrationAnswer] = Field(..., min_length=3, max_length=3)


class UserPublic(BaseModel):
    id: uuid.UUID
    email: str
    name: str
    department: str | None
    plan: str
    onboarding_complete: bool
    resume_parsed: bool
    target_companies: list[str] | None
    calibration_score: int | None
    created_at: datetime

    model_config = {"from_attributes": True}


class UserProfile(UserPublic):
    phone: str | None
    college: str | None
    graduation_year: int | None
    cgpa: float | None
    current_role: str | None
    preferred_language: str | None
    plan_expires_at: datetime | None
    sessions_used: int
    oa_solves_used: int
    last_active_at: datetime | None

    model_config = {"from_attributes": True}


class PlanInfo(BaseModel):
    plan: Literal["free", "student", "pro", "oa_pass"]
    sessions_limit: int | None
    oa_solves_limit: int | None
    group_mode_enabled: bool
    priority_routing: bool
    expires_at: datetime | None
