"""Pydantic v2 schemas for OA solver request/response."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class OACaptureRequest(BaseModel):
    screenshot_b64: str = Field(..., description="Base64-encoded PNG screenshot")
    session_id: str
    user_id: str
    department: str | None = None
    company: str | None = None


class ParsedQuestion(BaseModel):
    question_text: str
    question_type: Literal[
        "coding",
        "mcq_aptitude",
        "mcq_technical_cs",
        "mcq_technical_ece",
        "mcq_technical_mech",
        "mcq_technical_civil",
        "mcq_technical_chem",
        "debugging",
        "output_prediction",
    ]
    options: list[str] | None = None
    code_snippet: str | None = None
    constraints: str | None = None
    examples: str | None = None
    language_hint: str | None = None


class OASolveRequest(BaseModel):
    parsed_question: ParsedQuestion
    session_id: str
    user_id: str
    department: str | None = None
    company: str | None = None
    preferred_language: str = "Python"


class OASolution(BaseModel):
    question_type: str
    approach: str | None = None
    answer: str
    explanation: str
    code: str | None = None
    time_complexity: str | None = None
    space_complexity: str | None = None
    confidence: int = Field(..., ge=0, le=100)
    confidence_level: Literal["high", "medium", "low"]
    warning: str | None = None
    similar_question_found: bool = False


class OAContributeRequest(BaseModel):
    question_text: str = Field(..., min_length=10)
    question_type: str
    answer: str
    company: str
    department: str
    options: list[str] | None = None
    user_id: str
    session_id: str | None = None


class OAGroupBroadcast(BaseModel):
    group_code: str = Field(..., min_length=6, max_length=6)
    screenshot_b64: str
    sender_user_id: str
    session_id: str
