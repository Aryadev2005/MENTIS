"""Onboarding controller — resume upload, profile setup, calibration."""

import logging
import uuid
from typing import Any

from ..services.resume_parser import parse_resume
from ..models.schemas.user import (
    OnboardingStep1,
    OnboardingStep2,
    OnboardingStep3,
    OnboardingStep5,
    OnboardingStep6,
    OnboardingStep7,
    OnboardingStep8,
    UserPublic,
    UserProfile,
)
from ..models.vector.embeddings import embed_text
from ..database.redis_client import cache

logger = logging.getLogger(__name__)

CALIBRATION_QUESTIONS = {
    "CSE": [
        {
            "id": "cse_q1",
            "question": "What is the time complexity of binary search?",
            "options": ["O(n)", "O(log n)", "O(n log n)", "O(1)"],
            "correct": "O(log n)",
            "topic": "DSA",
        },
        {
            "id": "cse_q2",
            "question": "Which data structure is used in BFS traversal?",
            "options": ["Stack", "Queue", "Heap", "Tree"],
            "correct": "Queue",
            "topic": "DSA",
        },
        {
            "id": "cse_q3",
            "question": "What does ACID stand for in databases?",
            "options": [
                "Atomicity, Consistency, Isolation, Durability",
                "Access, Control, Insert, Delete",
                "Atomicity, Complexity, Isolation, Dependency",
                "None of the above",
            ],
            "correct": "Atomicity, Consistency, Isolation, Durability",
            "topic": "DBMS",
        },
    ],
    "ECE": [
        {
            "id": "ece_q1",
            "question": "What is the Nyquist sampling theorem?",
            "options": [
                "Sample at twice the highest frequency",
                "Sample at the signal frequency",
                "Sample at half the highest frequency",
                "Sample at any frequency",
            ],
            "correct": "Sample at twice the highest frequency",
            "topic": "Signals",
        },
        {
            "id": "ece_q2",
            "question": "What is the output of a NOT gate with input 1?",
            "options": ["0", "1", "Undefined", "High impedance"],
            "correct": "0",
            "topic": "Digital Electronics",
        },
        {
            "id": "ece_q3",
            "question": "Op-amp ideal input impedance is:",
            "options": ["Zero", "Infinite", "1 kΩ", "Depends on feedback"],
            "correct": "Infinite",
            "topic": "Circuits",
        },
    ],
}

DEFAULT_QUESTIONS = CALIBRATION_QUESTIONS["CSE"]


async def handle_resume_upload(
    file_bytes: bytes,
    filename: str,
    user_id: str,
    db_session: Any,
) -> dict[str, Any]:
    """Parse resume and store structured data."""
    parsed = await parse_resume(file_bytes, filename)

    skill_summary = parsed.get("skill_summary", "")
    if skill_summary:
        embedding = await embed_text(skill_summary)
    else:
        embedding = None

    from ..models.db.user import User
    from sqlalchemy import select

    stmt = select(User).where(User.id == uuid.UUID(user_id))
    result = await db_session.execute(stmt)
    user = result.scalar_one_or_none()

    if user:
        user.resume_parsed = True
        user.resume_summary = skill_summary
        if embedding:
            user.skill_embedding = embedding
        await db_session.commit()

    await cache.set(
        f"resume:{user_id}",
        parsed,
        ttl=86400 * 30,
    )

    logger.info(f"Resume parsed for user {user_id}: {len(parsed.get('skills', []))} skills found")
    return parsed


async def get_calibration_questions(department: str) -> list[dict]:
    """Return 3 calibration questions for a given department."""
    return CALIBRATION_QUESTIONS.get(department, DEFAULT_QUESTIONS)


async def score_calibration(
    answers: list[dict],
    department: str,
    user_id: str,
    db_session: Any,
) -> dict[str, Any]:
    """Score calibration answers and update user profile."""
    questions = CALIBRATION_QUESTIONS.get(department, DEFAULT_QUESTIONS)
    q_map = {q["id"]: q for q in questions}

    correct = 0
    for answer in answers:
        q = q_map.get(answer.get("question_id", ""))
        if q and answer.get("answer") == q["correct"]:
            correct += 1

    score = int((correct / len(questions)) * 100) if questions else 0

    from ..models.db.user import User
    from sqlalchemy import select

    stmt = select(User).where(User.id == uuid.UUID(user_id))
    result = await db_session.execute(stmt)
    user = result.scalar_one_or_none()

    if user:
        user.calibration_score = score
        await db_session.commit()

    level = "beginner" if score < 40 else ("intermediate" if score < 75 else "advanced")

    return {
        "score": score,
        "correct": correct,
        "total": len(questions),
        "level": level,
        "message": f"You scored {score}/100. Level: {level.capitalize()}.",
    }


async def complete_onboarding(user_id: str, db_session: Any) -> UserProfile:
    """Mark onboarding as complete and generate study plan."""
    from ..models.db.user import User
    from sqlalchemy import select

    stmt = select(User).where(User.id == uuid.UUID(user_id))
    result = await db_session.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise ValueError(f"User not found: {user_id}")

    user.onboarding_complete = True
    await db_session.commit()
    await db_session.refresh(user)

    logger.info(f"Onboarding complete for user {user_id}")
    return UserProfile.model_validate(user)
