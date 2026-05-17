"""Interview controller — business logic for live interview answer generation."""

import asyncio
import hashlib
import logging
import time
from typing import AsyncIterator

from ..agents.interview_agent import interview_graph, InterviewState, node_retrieve_context, node_generate_answer_streaming
from ..services.claude_service import detect_question, stream_answer, score_answer
from ..models.schemas.interview import (
    TranscriptInput,
    InterviewRequest,
    AnswerComplete,
    SessionStartRequest,
    SessionStartResponse,
    QuestionDetection,
)
from ..database.redis_client import cache, SessionContext
from ..database.postgres import get_db

logger = logging.getLogger(__name__)

REDIS_ANSWER_TTL = 86400 * 7


async def handle_transcript(
    input_data: TranscriptInput,
    user_context: dict,
) -> QuestionDetection:
    """Detect if a transcript fragment contains an interview question."""
    result = await detect_question(input_data.transcript)
    return QuestionDetection(
        is_question=result.get("is_question", False),
        question=result.get("question"),
        question_type=result.get("type"),
        confidence=0.9 if result.get("is_question") else 0.1,
    )


async def stream_interview_answer(
    request: InterviewRequest,
    user_context: dict,
) -> AsyncIterator[str]:
    """Stream answer tokens for a detected interview question."""
    cache_key = f"answer:{hashlib.sha256(request.question.lower().strip().encode()).hexdigest()[:16]}"
    cached = await cache.get(cache_key)
    if cached:
        logger.info(f"Cache hit for question: {request.question[:50]}")
        yield cached["answer"]
        return

    resume_summary = user_context.get("resume_summary", "No resume data.")
    jd_keywords = user_context.get("jd_keywords", "Not provided.")

    session_ctx = SessionContext(request.session_id)
    recent_qa = await session_ctx.get_recent_qa(n=3)

    from ..models.vector.qdrant_client import interview_question_store, user_memory_store
    qdrant_results, memory_results = await asyncio.gather(
        interview_question_store.search(request.question, limit=3, cache=cache),
        user_memory_store.retrieve_similar(request.user_id, request.question, limit=2, cache=cache),
        return_exceptions=True,
    )

    context_parts = []
    if isinstance(qdrant_results, list):
        for r in qdrant_results[:2]:
            p = r.get("payload", {})
            if p.get("answer"):
                context_parts.append(f"Similar Q: {p.get('question', '')[:200]}\nA: {p.get('answer', '')[:350]}")

    system_prompt = f"""You are a career coach helping {user_context.get('name', 'the candidate')}, a {request.department or 'Engineering'} professional with these skills: {user_context.get('skills_summary', 'various engineering skills')}.

They are interviewing at {request.company or 'a top company'} for {request.role or 'Software Engineer'}.

Resume highlights: {resume_summary[:500]}
JD keywords: {jd_keywords[:200]}

RULES:
- Natural, confident, specific answer
- NEVER invent experience not in their resume
- Behavioral questions: STAR format
- Under 120 words
- Sound human, not robotic"""

    full_answer = ""
    start = time.perf_counter()

    async for token in stream_answer(
        question=request.question,
        system_prompt=system_prompt,
        context="\n\n".join(context_parts),
    ):
        full_answer += token
        yield token

    elapsed = round((time.perf_counter() - start) * 1000)
    logger.info(f"Answer streamed in {elapsed}ms for question type: {request.question_type}")

    await cache.set(cache_key, {"answer": full_answer, "question_type": request.question_type}, ttl=REDIS_ANSWER_TTL)

    confidence = await score_answer(request.question, full_answer)
    await session_ctx.push_qa(request.question, full_answer, confidence)


async def get_answer_confidence(question: str, answer: str) -> dict:
    """Score a completed answer."""
    score = await score_answer(question, answer)
    warning = None
    if score < 70:
        warning = "Framework answer — verify against your actual experience."
    return {
        "confidence": score,
        "warning": warning,
        "color": "green" if score >= 85 else ("yellow" if score >= 65 else "red"),
    }


async def start_session(
    request: SessionStartRequest,
    user_id: str,
    db_session: object,
) -> SessionStartResponse:
    """Initialize a new interview/OA session and generate pre-session brief."""
    from ..models.db.question import Company
    from sqlalchemy import select

    session_id = f"sess_{int(time.time())}_{user_id[:8]}"

    company_brief = ""
    oa_format = None

    stmt = select(Company).where(Company.name == request.company)
    result = await db_session.execute(stmt)
    company = result.scalar_one_or_none()

    if company and company.oa_format:
        oa_format = company.oa_format
        sections = oa_format.get("sections", [])
        brief_parts = [f"{request.company}'s OA typically includes:"]
        for section in sections[:4]:
            brief_parts.append(f"  • {section.get('name', '')}: {section.get('count', '?')} questions ({section.get('duration_mins', '?')} mins)")
        company_brief = "\n".join(brief_parts)
    else:
        company_brief = f"Starting your {request.mode} session with {request.company}. Good luck!"

    await cache.set(
        f"session_meta:{session_id}",
        {
            "user_id": user_id,
            "company": request.company,
            "role": request.role,
            "department": request.department,
            "mode": request.mode,
        },
        ttl=14400,
    )

    return SessionStartResponse(
        session_id=session_id,
        pre_session_brief=company_brief,
        oa_format=oa_format,
    )
