"""LangGraph interview answer agent — 6 nodes, sub-2s end-to-end."""

import asyncio
import logging
import time
from typing import Any, AsyncIterator, TypedDict, Annotated

from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages

from ..services.claude_service import (
    detect_question,
    stream_answer,
    score_answer,
)
from ..models.vector.qdrant_client import (
    interview_question_store,
    user_memory_store,
)
from ..database.redis_client import SessionContext, cache

logger = logging.getLogger(__name__)

ANSWER_SYSTEM_PROMPT_TEMPLATE = """You are a career coach helping {name}, a {department} engineer, ace their interview at {company} for the role of {role}.

Their resume highlights:
{resume_summary}

Key competencies from the job description:
{jd_keywords}

INSTRUCTIONS:
- Generate a natural, confident, specific answer
- NEVER invent experience not in their resume
- For behavioral questions: use STAR format (Situation, Task, Action, Result)
- Keep answer under 120 words
- Sound human and conversational, not robotic
- Be India-context-aware
- Reference actual projects/skills from their resume when relevant"""


class InterviewState(TypedDict):
    transcript: str
    session_id: str
    user_id: str
    user_name: str
    company: str
    role: str
    department: str
    resume_summary: str
    jd_keywords: str
    question: str | None
    question_type: str | None
    is_question: bool
    retrieved_context: str
    answer: str
    confidence: int
    warning: str | None
    latency_ms: int
    start_time: float
    error: str | None


async def node_detect_question(state: InterviewState) -> dict:
    """Node 2: Detect if transcript contains a question."""
    result = await detect_question(state["transcript"])
    return {
        "is_question": result.get("is_question", False),
        "question": result.get("question"),
        "question_type": result.get("type"),
    }


async def node_retrieve_context(state: InterviewState) -> dict:
    """Node 3: Parallel retrieval from Qdrant + Redis."""
    if not state.get("question"):
        return {"retrieved_context": ""}

    qdrant_task = interview_question_store.search(
        query=state["question"],
        limit=3,
        filters={"company": state["company"]} if state.get("company") else None,
        cache=cache,
    )

    memory_task = user_memory_store.retrieve_similar(
        user_id=state["user_id"],
        question=state["question"],
        limit=2,
        cache=cache,
    )

    session_ctx = SessionContext(state["session_id"])
    recent_qa_task = session_ctx.get_recent_qa(n=3)

    qdrant_results, memory_results, recent_qa = await asyncio.gather(
        qdrant_task, memory_task, recent_qa_task, return_exceptions=True
    )

    context_parts: list[str] = []

    if isinstance(qdrant_results, list) and qdrant_results:
        for r in qdrant_results[:3]:
            payload = r.get("payload", {})
            if payload.get("answer"):
                context_parts.append(
                    f"[Similar question] Q: {payload.get('question', '')[:200]}\n"
                    f"A: {payload.get('answer', '')[:400]}"
                )

    if isinstance(memory_results, list) and memory_results:
        for r in memory_results[:2]:
            payload = r.get("payload", {})
            if payload.get("answer") and r.get("score", 0) > 0.8:
                context_parts.append(
                    f"[Your past answer] Q: {payload.get('question', '')[:200]}\n"
                    f"A: {payload.get('answer', '')[:300]}"
                )

    if isinstance(recent_qa, list) and recent_qa:
        for qa in recent_qa[:2]:
            context_parts.append(
                f"[Earlier in session] Q: {qa.get('question', '')[:150]}\n"
                f"A: {qa.get('answer', '')[:200]}"
            )

    return {"retrieved_context": "\n\n".join(context_parts[:5])}


async def node_generate_answer_streaming(
    state: InterviewState,
) -> AsyncIterator[dict]:
    """Node 4: Stream answer tokens from Claude. Yields partial states."""
    system_prompt = ANSWER_SYSTEM_PROMPT_TEMPLATE.format(
        name=state.get("user_name", "the candidate"),
        department=state.get("department", "Engineering"),
        company=state.get("company", "the company"),
        role=state.get("role", "Software Engineer"),
        resume_summary=state.get("resume_summary", "No resume data available."),
        jd_keywords=state.get("jd_keywords", "Not specified."),
    )

    full_answer = ""
    async for token in stream_answer(
        question=state["question"] or "",
        system_prompt=system_prompt,
        context=state.get("retrieved_context", ""),
        max_tokens=300,
    ):
        full_answer += token
        yield {"answer": full_answer, "_stream_token": token}

    elapsed = round((time.perf_counter() - state["start_time"]) * 1000)
    yield {"answer": full_answer, "latency_ms": elapsed}


async def node_score_confidence(state: InterviewState) -> dict:
    """Node 5: Score answer quality (runs after streaming completes)."""
    if not state.get("answer") or not state.get("question"):
        return {"confidence": 70, "warning": None}

    score = await score_answer(state["question"], state["answer"])

    warning = None
    if score < 70:
        warning = "Framework answer — verify this against your actual experience before using."

    return {"confidence": score, "warning": warning}


async def node_learn(state: InterviewState) -> dict:
    """Node 6: Async learning — store Q&A, update skill vector. Non-blocking."""
    if not state.get("question") or not state.get("answer"):
        return {}

    asyncio.create_task(
        _async_learn(
            user_id=state["user_id"],
            session_id=state["session_id"],
            question=state["question"],
            answer=state["answer"],
            confidence=state.get("confidence", 70),
            question_type=state.get("question_type", "technical"),
        )
    )

    session_ctx = SessionContext(state["session_id"])
    await session_ctx.push_qa(
        question=state["question"],
        answer=state["answer"],
        confidence=state.get("confidence", 70),
    )

    return {}


async def _async_learn(
    user_id: str,
    session_id: str,
    question: str,
    answer: str,
    confidence: int,
    question_type: str,
) -> None:
    try:
        await user_memory_store.store_qa(
            user_id=user_id,
            session_id=session_id,
            question=question,
            answer=answer,
            confidence=confidence,
            question_type=question_type,
        )
    except Exception as e:
        logger.error(f"Async learn failed: {e}")


def route_after_detection(state: InterviewState) -> str:
    if state.get("is_question"):
        return "retrieve_context"
    return END


def build_interview_graph() -> StateGraph:
    graph = StateGraph(InterviewState)

    graph.add_node("detect_question", node_detect_question)
    graph.add_node("retrieve_context", node_retrieve_context)
    graph.add_node("score_confidence", node_score_confidence)
    graph.add_node("learn", node_learn)

    graph.set_entry_point("detect_question")

    graph.add_conditional_edges(
        "detect_question",
        route_after_detection,
        {
            "retrieve_context": "retrieve_context",
            END: END,
        },
    )
    graph.add_edge("retrieve_context", "score_confidence")
    graph.add_edge("score_confidence", "learn")
    graph.add_edge("learn", END)

    return graph.compile()


interview_graph = build_interview_graph()
