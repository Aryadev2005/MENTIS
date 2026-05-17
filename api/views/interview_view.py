"""Response serializers for interview endpoints."""

from dataclasses import dataclass
from typing import Any


@dataclass
class AnswerStreamEvent:
    token: str
    session_id: str

    def to_sse(self) -> str:
        return f"data: {self.token}\n\n"


@dataclass
class AnswerCompleteView:
    session_id: str
    question: str
    answer: str
    confidence: int
    confidence_color: str
    warning: str | None
    latency_ms: int

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AnswerCompleteView":
        confidence = data.get("confidence", 70)
        return cls(
            session_id=data.get("session_id", ""),
            question=data.get("question", ""),
            answer=data.get("answer", ""),
            confidence=confidence,
            confidence_color=cls._color(confidence),
            warning=data.get("warning"),
            latency_ms=data.get("latency_ms", 0),
        )

    @staticmethod
    def _color(confidence: int) -> str:
        if confidence >= 85:
            return "green"
        if confidence >= 65:
            return "yellow"
        return "red"

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "question": self.question,
            "answer": self.answer,
            "confidence": self.confidence,
            "confidence_color": self.confidence_color,
            "warning": self.warning,
            "latency_ms": self.latency_ms,
        }
