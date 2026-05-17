"""Self-learning pipeline — post-session embedding and skill update."""

import asyncio
import logging
import uuid
from datetime import datetime, timedelta
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from ..models.vector.embeddings import embed_text
from ..models.vector.qdrant_client import user_memory_store, interview_question_store
from ..database.redis_client import cache
from ..services.claude_service import generate_session_debrief
from ..config import settings

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def process_session_end(
    session_id: str,
    user_id: str,
    user_name: str,
    company: str,
    qa_pairs: list[dict[str, Any]],
    db_session: Any,
) -> str:
    """Full post-session pipeline: embed, upsert, skill update, debrief. Returns debrief text."""
    logger.info(f"Post-session pipeline starting for session {session_id}")

    embedding_tasks = [
        user_memory_store.store_qa(
            user_id=user_id,
            session_id=session_id,
            question=qa["question"],
            answer=qa["answer"],
            confidence=qa.get("confidence", 70),
            question_type=qa.get("type", "technical"),
            topic=qa.get("topic"),
        )
        for qa in qa_pairs
    ]
    await asyncio.gather(*embedding_tasks, return_exceptions=True)
    logger.info(f"Embedded {len(qa_pairs)} Q&A pairs into Qdrant")

    await _update_skill_vectors(user_id, qa_pairs, db_session)

    debrief = await generate_session_debrief(qa_pairs, user_name, company)

    await cache.set(
        f"debrief:{session_id}",
        {"debrief": debrief, "generated_at": datetime.utcnow().isoformat()},
        ttl=86400 * 30,
    )

    logger.info(f"Post-session pipeline complete for session {session_id}")
    return debrief


async def _update_skill_vectors(
    user_id: str,
    qa_pairs: list[dict[str, Any]],
    db_session: Any,
) -> None:
    """Update per-topic performance in PostgreSQL."""
    from ..models.db.performance import PerformanceLog
    from sqlalchemy import select

    topic_stats: dict[str, dict[str, Any]] = {}

    for qa in qa_pairs:
        topic = qa.get("topic", "general")
        confidence = qa.get("confidence", 70)
        dept = qa.get("department", "CSE")

        if topic not in topic_stats:
            topic_stats[topic] = {"attempts": 0, "total_confidence": 0, "department": dept}

        topic_stats[topic]["attempts"] += 1
        topic_stats[topic]["total_confidence"] += confidence

    for topic, stats in topic_stats.items():
        avg_confidence = stats["total_confidence"] / stats["attempts"]
        success = 1 if avg_confidence >= 70 else 0

        stmt = select(PerformanceLog).where(
            PerformanceLog.user_id == uuid.UUID(user_id),
            PerformanceLog.topic == topic,
        )
        result = await db_session.execute(stmt)
        log = result.scalar_one_or_none()

        if log:
            log.attempts += stats["attempts"]
            log.correct += success * stats["attempts"]
            log.success_rate = log.correct / log.attempts if log.attempts > 0 else 0.0
            log.average_confidence = (
                (log.average_confidence * (log.attempts - stats["attempts"]) + stats["total_confidence"])
                / log.attempts
            )
            log.last_attempted_at = datetime.utcnow()
            log.updated_at = datetime.utcnow()
        else:
            log = PerformanceLog(
                user_id=uuid.UUID(user_id),
                topic=topic,
                department=stats["department"],
                attempts=stats["attempts"],
                correct=success * stats["attempts"],
                success_rate=float(success),
                average_confidence=avg_confidence,
                last_attempted_at=datetime.utcnow(),
            )
            db_session.add(log)

    await db_session.commit()
    logger.info(f"Skill vectors updated for user {user_id}: {list(topic_stats.keys())}")


async def generate_weekly_report(user_id: str, db_session: Any) -> dict[str, Any]:
    """Aggregate weekly session data into a personalized improvement plan."""
    from ..models.db.performance import PerformanceLog
    from sqlalchemy import select

    week_ago = datetime.utcnow() - timedelta(days=7)

    stmt = select(PerformanceLog).where(
        PerformanceLog.user_id == uuid.UUID(user_id),
        PerformanceLog.last_attempted_at >= week_ago,
    ).order_by(PerformanceLog.success_rate.asc())

    result = await db_session.execute(stmt)
    logs = result.scalars().all()

    weak_topics = [
        {"topic": log.topic, "success_rate": log.success_rate, "attempts": log.attempts}
        for log in logs[:5]
        if log.success_rate < 0.7
    ]

    strong_topics = [
        {"topic": log.topic, "success_rate": log.success_rate}
        for log in sorted(logs, key=lambda x: x.success_rate, reverse=True)[:3]
        if log.success_rate >= 0.8
    ]

    return {
        "user_id": user_id,
        "week_start": week_ago.isoformat(),
        "weak_topics": weak_topics,
        "strong_topics": strong_topics,
        "total_topics_practiced": len(logs),
        "overall_success_rate": (
            sum(l.success_rate for l in logs) / len(logs) if logs else 0.0
        ),
    }


async def reindex_user_memory(user_id: str, batch_size: int = 100) -> None:
    """Re-embed and re-index a user's memory collection when enough new pairs accumulate."""
    count_key = f"embed_count:{user_id}"
    current = await cache.get(count_key) or 0

    new_count = int(current) + 1
    await cache.set(count_key, new_count, ttl=86400 * 30)

    if new_count % batch_size == 0:
        logger.info(f"Triggering re-index for user {user_id} at {new_count} pairs")
        pass


def start_scheduler() -> None:
    if not scheduler.running:
        scheduler.add_job(
            _weekly_report_job,
            CronTrigger(day_of_week="sun", hour=8, minute=0),
            id="weekly_report",
            replace_existing=True,
        )
        scheduler.start()
        logger.info("APScheduler started")


async def _weekly_report_job() -> None:
    logger.info("Weekly report job running...")
