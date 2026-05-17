"""Analytics controller — performance data, readiness scores, skill radar."""

import logging
import uuid
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select, func
from ..models.db.performance import PerformanceLog
from ..models.db.session import Session
from ..database.redis_client import cache

logger = logging.getLogger(__name__)

DEPARTMENT_TOPICS = {
    "CSE": ["DSA", "OS", "DBMS", "Networks", "OOP", "System Design", "Aptitude", "HR"],
    "ECE": ["Circuits", "Digital Electronics", "Signals", "Communications", "VLSI", "Microprocessors", "Aptitude", "HR"],
    "Mechanical": ["Thermodynamics", "Fluid Mechanics", "Manufacturing", "SOM", "Machine Design", "Aptitude", "HR"],
    "Civil": ["Structural Analysis", "Geotechnical", "Transportation", "Environmental", "Fluid", "Aptitude", "HR"],
    "Chemical": ["Mass Transfer", "Heat Transfer", "Reaction Engineering", "Process Control", "Thermodynamics", "Aptitude", "HR"],
    "EEE": ["Power Systems", "Machines", "Control Systems", "Power Electronics", "Circuits", "Aptitude", "HR"],
}


async def get_skill_radar(user_id: str, department: str, db_session: Any) -> dict[str, Any]:
    """Return 8-dim skill radar data for the user's department."""
    cache_key = f"radar:{user_id}:{department}"
    cached = await cache.get(cache_key)
    if cached:
        return cached

    topics = DEPARTMENT_TOPICS.get(department, DEPARTMENT_TOPICS["CSE"])

    stmt = select(PerformanceLog).where(
        PerformanceLog.user_id == uuid.UUID(user_id),
        PerformanceLog.department == department,
    )
    result = await db_session.execute(stmt)
    logs = result.scalars().all()

    log_map = {log.topic: log for log in logs}

    radar_data = []
    for topic in topics:
        log = log_map.get(topic)
        radar_data.append({
            "topic": topic,
            "score": round(log.success_rate * 100) if log else 0,
            "attempts": log.attempts if log else 0,
            "avg_confidence": round(log.average_confidence) if log else 0,
        })

    response = {
        "department": department,
        "topics": radar_data,
        "overall": round(sum(r["score"] for r in radar_data) / len(radar_data)),
    }

    await cache.set(cache_key, response, ttl=300)
    return response


async def get_company_readiness(
    user_id: str,
    company: str,
    department: str,
    db_session: Any,
) -> dict[str, Any]:
    """Calculate a company readiness score 0-100."""
    stmt = select(PerformanceLog).where(
        PerformanceLog.user_id == uuid.UUID(user_id),
        PerformanceLog.company == company,
    )
    result = await db_session.execute(stmt)
    company_logs = result.scalars().all()

    stmt2 = select(PerformanceLog).where(
        PerformanceLog.user_id == uuid.UUID(user_id),
        PerformanceLog.department == department,
    )
    result2 = await db_session.execute(stmt2)
    dept_logs = result2.scalars().all()

    all_logs = company_logs + dept_logs
    if not all_logs:
        return {
            "company": company,
            "readiness_score": 0,
            "message": f"No data yet. Start a practice session for {company}!",
            "weak_topics": [],
            "strong_topics": [],
        }

    scores = [log.success_rate * 100 for log in all_logs]
    readiness = round(sum(scores) / len(scores))

    weak = [
        {"topic": log.topic, "score": round(log.success_rate * 100)}
        for log in sorted(all_logs, key=lambda x: x.success_rate)[:3]
        if log.success_rate < 0.7
    ]

    strong = [
        {"topic": log.topic, "score": round(log.success_rate * 100)}
        for log in sorted(all_logs, key=lambda x: x.success_rate, reverse=True)[:2]
        if log.success_rate >= 0.8
    ]

    return {
        "company": company,
        "readiness_score": readiness,
        "message": f"You are {readiness}% ready for {company} OA.",
        "weak_topics": weak,
        "strong_topics": strong,
    }


async def get_session_heatmap(user_id: str, days: int = 90, db_session: Any = None) -> list[dict]:
    """GitHub-style session heatmap for the last N days."""
    start_date = datetime.utcnow() - timedelta(days=days)

    stmt = (
        select(
            func.date(Session.started_at).label("date"),
            func.count(Session.id).label("count"),
        )
        .where(
            Session.user_id == uuid.UUID(user_id),
            Session.started_at >= start_date,
        )
        .group_by(func.date(Session.started_at))
    )

    result = await db_session.execute(stmt)
    rows = result.all()

    return [
        {"date": str(row.date), "count": row.count, "level": min(4, row.count)}
        for row in rows
    ]


async def get_improvement_trend(user_id: str, db_session: Any) -> list[dict]:
    """Line chart data: answer quality over time (last 10 sessions)."""
    stmt = (
        select(Session)
        .where(
            Session.user_id == uuid.UUID(user_id),
            Session.average_confidence.isnot(None),
        )
        .order_by(Session.started_at.desc())
        .limit(10)
    )

    result = await db_session.execute(stmt)
    sessions = result.scalars().all()

    return [
        {
            "session_id": str(s.id),
            "date": s.started_at.isoformat(),
            "company": s.company,
            "average_confidence": round(s.average_confidence),
            "qa_count": s.qa_count,
        }
        for s in reversed(sessions)
    ]
