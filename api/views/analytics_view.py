"""Response serializers for analytics endpoints."""

from dataclasses import dataclass
from typing import Any


@dataclass
class SkillRadarView:
    department: str
    topics: list[dict[str, Any]]
    overall: int
    grade: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SkillRadarView":
        overall = data.get("overall", 0)
        return cls(
            department=data.get("department", ""),
            topics=data.get("topics", []),
            overall=overall,
            grade=cls._grade(overall),
        )

    @staticmethod
    def _grade(score: int) -> str:
        if score >= 85:
            return "S"
        if score >= 70:
            return "A"
        if score >= 55:
            return "B"
        if score >= 40:
            return "C"
        return "D"

    def to_dict(self) -> dict[str, Any]:
        return {
            "department": self.department,
            "topics": self.topics,
            "overall": self.overall,
            "grade": self.grade,
        }
