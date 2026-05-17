"""OA controller — business logic for OA question solving."""

import logging
from typing import Any

from ..agents.oa_agent import oa_graph, OAState
from ..models.schemas.oa import (
    OACaptureRequest,
    OASolveRequest,
    OASolution,
    OAContributeRequest,
)
from ..models.vector.qdrant_client import oa_question_store
from ..database.redis_client import cache

logger = logging.getLogger(__name__)


async def solve_oa_question(
    request: OASolveRequest,
    user_context: dict[str, Any],
) -> OASolution:
    """Run the full OA solving pipeline via LangGraph."""
    initial_state: OAState = {
        "screenshot_b64": "",
        "session_id": request.session_id,
        "user_id": request.user_id,
        "department": request.department or user_context.get("department"),
        "company": request.company,
        "preferred_language": request.preferred_language or user_context.get("preferred_language", "Python"),
        "parsed_question": request.parsed_question.model_dump(),
        "question_type": request.parsed_question.question_type,
        "retrieved_context": "",
        "solution": "",
        "approach": None,
        "code": None,
        "time_complexity": None,
        "confidence": 0,
        "confidence_level": "low",
        "warning": None,
        "similar_found": False,
        "error": None,
    }

    final_state = await oa_graph.ainvoke(initial_state)

    return OASolution(
        question_type=final_state.get("question_type", "unknown"),
        approach=final_state.get("approach"),
        answer=final_state.get("solution", ""),
        explanation=final_state.get("solution", ""),
        code=final_state.get("code"),
        time_complexity=final_state.get("time_complexity"),
        space_complexity=None,
        confidence=final_state.get("confidence", 0),
        confidence_level=final_state.get("confidence_level", "low"),
        warning=final_state.get("warning"),
        similar_question_found=final_state.get("similar_found", False),
    )


async def capture_and_solve(
    request: OACaptureRequest,
    user_context: dict[str, Any],
) -> OASolution:
    """Full pipeline: screenshot → parse → solve."""
    initial_state: OAState = {
        "screenshot_b64": request.screenshot_b64,
        "session_id": request.session_id,
        "user_id": request.user_id,
        "department": request.department or user_context.get("department"),
        "company": request.company,
        "preferred_language": user_context.get("preferred_language", "Python"),
        "parsed_question": {},
        "question_type": None,
        "retrieved_context": "",
        "solution": "",
        "approach": None,
        "code": None,
        "time_complexity": None,
        "confidence": 0,
        "confidence_level": "low",
        "warning": None,
        "similar_found": False,
        "error": None,
    }

    final_state = await oa_graph.ainvoke(initial_state)

    return OASolution(
        question_type=final_state.get("question_type", "unknown"),
        approach=final_state.get("approach"),
        answer=final_state.get("solution", ""),
        explanation=final_state.get("solution", ""),
        code=final_state.get("code"),
        time_complexity=final_state.get("time_complexity"),
        space_complexity=None,
        confidence=final_state.get("confidence", 0),
        confidence_level=final_state.get("confidence_level", "low"),
        warning=final_state.get("warning"),
        similar_question_found=final_state.get("similar_found", False),
    )


async def contribute_question(request: OAContributeRequest) -> str:
    """Store a user-contributed OA question in the shared database."""
    question_id = await oa_question_store.upsert_question(
        question_text=request.question_text,
        answer_text=request.answer,
        payload={
            "question_type": request.question_type,
            "company": request.company,
            "department": request.department,
            "options": request.options,
            "verified": False,
            "contributed_by": request.user_id,
        },
    )

    logger.info(f"Question contributed to OA bank: {question_id} (company={request.company})")
    return question_id


async def get_company_oa_brief(company: str, department: str) -> dict[str, Any]:
    """Fetch company-specific OA format and generate a pre-session brief."""
    cache_key = f"oa_brief:{company}:{department}"
    cached = await cache.get(cache_key)
    if cached:
        return cached

    brief = {
        "company": company,
        "department": department,
        "message": f"Prepare for {company}'s OA. Questions will be routed to the {department} solver.",
        "oa_format": None,
    }

    await cache.set(cache_key, brief, ttl=3600)
    return brief
