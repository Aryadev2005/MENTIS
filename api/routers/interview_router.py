"""FastAPI router for live interview copilot endpoints."""

from typing import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from slowapi import Limiter
from slowapi.util import get_remote_address

from ..controllers.interview_controller import (
    handle_transcript,
    stream_interview_answer,
    get_answer_confidence,
    start_session,
)
from ..models.schemas.interview import (
    TranscriptInput,
    InterviewRequest,
    SessionStartRequest,
    SessionStartResponse,
    FeedbackRequest,
    QuestionDetection,
    AnswerComplete,
)
from ..database.postgres import get_db
from ..database.redis_client import cache
from ..controllers.jd_controller import extract_jd_keywords
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


async def get_user_context(request: Request) -> dict:
    """Extract user context from request headers (set by Electron)."""
    return {
        "user_id": request.headers.get("X-User-Id", ""),
        "name": request.headers.get("X-User-Name", ""),
        "department": request.headers.get("X-Department", "CSE"),
        "skills_summary": request.headers.get("X-Skills", ""),
        "resume_summary": await _get_resume_summary(request.headers.get("X-User-Id", "")),
        "jd_keywords": request.headers.get("X-JD-Keywords", ""),
    }


async def _get_resume_summary(user_id: str) -> str:
    if not user_id:
        return ""
    cached = await cache.get(f"resume:{user_id}")
    if cached:
        return cached.get("skill_summary", "")
    return ""


@router.post("/session/start", response_model=SessionStartResponse)
@limiter.limit("10/minute")
async def start_interview_session(
    request: Request,
    body: SessionStartRequest,
    db: AsyncSession = Depends(get_db),
) -> SessionStartResponse:
    """Initialize a new interview session."""
    user_id = request.headers.get("X-User-Id", "")
    if not user_id:
        raise HTTPException(status_code=401, detail="User ID required")

    return await start_session(body, user_id, db)


@router.post("/detect", response_model=QuestionDetection)
@limiter.limit("60/minute")
async def detect_interview_question(
    request: Request,
    body: TranscriptInput,
) -> QuestionDetection:
    """Detect if a transcript fragment contains an interview question."""
    user_context = await get_user_context(request)
    return await handle_transcript(body, user_context)


@router.post("/answer/stream")
@limiter.limit("30/minute")
async def stream_answer(
    request: Request,
    body: InterviewRequest,
) -> StreamingResponse:
    """Stream answer tokens for a detected interview question."""
    user_context = await get_user_context(request)

    async def token_generator() -> AsyncIterator[str]:
        async for token in stream_interview_answer(body, user_context):
            yield f"data: {token}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        token_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/answer/confidence")
async def score_confidence(
    question: str,
    answer: str,
) -> dict:
    """Score a completed answer's quality."""
    return await get_answer_confidence(question, answer)


@router.post("/jd/extract")
@limiter.limit("20/minute")
async def extract_job_description(
    request: Request,
    body: dict,
) -> dict:
    """Extract key competencies from a job description."""
    jd_text = body.get("jd_text", "")
    if len(jd_text) < 50:
        raise HTTPException(status_code=400, detail="JD text too short")
    keywords = await extract_jd_keywords(jd_text)
    return {"keywords": keywords}


@router.post("/feedback")
@limiter.limit("100/minute")
async def submit_feedback(
    request: Request,
    body: FeedbackRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Submit feedback on a generated answer."""
    from ..models.db.question import Question
    from sqlalchemy import select
    import uuid

    try:
        stmt = select(Question).where(Question.id == uuid.UUID(body.question_id))
        result = await db.execute(stmt)
        question = result.scalar_one_or_none()

        if question:
            question.user_feedback = body.feedback
            await db.commit()

        return {"status": "ok", "message": "Feedback recorded. Thank you!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
