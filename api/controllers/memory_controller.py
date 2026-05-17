"""Memory controller — user memory CRUD operations."""

import logging
from typing import Any

from ..agents.memory_agent import store_memory, retrieve_memories, get_user_weakness_summary
from ..services.self_learning import process_session_end

logger = logging.getLogger(__name__)


async def get_user_memories(
    user_id: str,
    query: str = "interview performance",
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Retrieve relevant memories for a user."""
    return await retrieve_memories(user_id=user_id, query=query, limit=limit)


async def add_user_memory(
    user_id: str,
    content: str,
    metadata: dict | None = None,
) -> str:
    """Manually store a memory for a user."""
    return await store_memory(user_id=user_id, content=content, metadata=metadata)


async def get_weakness_context(user_id: str) -> str:
    """Get weakness summary for prompt injection."""
    return await get_user_weakness_summary(user_id=user_id)


async def trigger_post_session_learning(
    session_id: str,
    user_id: str,
    user_name: str,
    company: str,
    qa_pairs: list[dict[str, Any]],
    db_session: Any,
) -> str:
    """Trigger the post-session self-learning pipeline."""
    debrief = await process_session_end(
        session_id=session_id,
        user_id=user_id,
        user_name=user_name,
        company=company,
        qa_pairs=qa_pairs,
        db_session=db_session,
    )
    logger.info(f"Post-session learning complete for session {session_id}")
    return debrief
