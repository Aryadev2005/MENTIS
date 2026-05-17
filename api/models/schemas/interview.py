"""Pydantic v2 schemas for interview-related request/response."""

from __future__ import annotations

import uuid
from typing import Literal

from pydantic import BaseModel, Field


class TranscriptInput(BaseModel):
    transcript: str = Field(..., min_length=1, max_length=2000)
    session_id: str
    language: str = "en-IN"


class QuestionDetection(BaseModel):
    is_question: bool
    question: str | None = None
    question_type: Literal["behavioral", "technical", "hr", "coding"] | None = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class InterviewRequest(BaseModel):
    question: str = Field(..., min_length=5, max_length=1000)
    question_type: Literal["behavioral", "technical", "hr", "coding"]
    session_id: str
    user_id: str
    company: str | None = None
    role: str | None = None
    department: str | None = None


class AnswerChunk(BaseModel):
    token: str
    session_id: str
    is_final: bool = False


class AnswerComplete(BaseModel):
    session_id: str
    question: str
    answer: str
    confidence: int = Field(..., ge=0, le=100)
    question_type: str
    warning: str | None = None
    latency_ms: int | None = None


class SessionStartRequest(BaseModel):
    company: str = Field(..., min_length=1, max_length=128)
    role: str = Field(..., min_length=1, max_length=256)
    department: str = Field(..., min_length=1, max_length=64)
    mode: Literal["interview", "oa", "mock"] = "interview"
    job_description: str | None = Field(None, max_length=5000)


class SessionStartResponse(BaseModel):
    session_id: str
    pre_session_brief: str
    oa_format: dict | None = None


class FeedbackRequest(BaseModel):
    question_id: str
    feedback: Literal["helpful", "not_helpful", "partially_helpful"]
    comment: str | None = Field(None, max_length=500)
