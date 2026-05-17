"""Response serializers for OA solver endpoints."""

from dataclasses import dataclass
from typing import Any


@dataclass
class OASolutionView:
    question_type: str
    answer: str
    explanation: str
    code: str | None
    approach: str | None
    time_complexity: str | None
    confidence: int
    confidence_color: str
    confidence_label: str
    warning: str | None
    similar_found: bool

    @classmethod
    def from_solution(cls, solution: Any) -> "OASolutionView":
        confidence = solution.confidence
        return cls(
            question_type=solution.question_type,
            answer=solution.answer,
            explanation=solution.explanation,
            code=solution.code,
            approach=solution.approach,
            time_complexity=solution.time_complexity,
            confidence=confidence,
            confidence_color="green" if confidence >= 85 else ("yellow" if confidence >= 65 else "red"),
            confidence_label="High" if confidence >= 85 else ("Medium" if confidence >= 65 else "Low — Verify"),
            warning=solution.warning,
            similar_found=solution.similar_question_found,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "question_type": self.question_type,
            "answer": self.answer,
            "explanation": self.explanation,
            "code": self.code,
            "approach": self.approach,
            "time_complexity": self.time_complexity,
            "confidence": self.confidence,
            "confidence_color": self.confidence_color,
            "confidence_label": self.confidence_label,
            "warning": self.warning,
            "similar_found": self.similar_found,
        }
