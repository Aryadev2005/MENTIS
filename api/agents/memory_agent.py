"""Long-term memory retrieval agent using Mem0."""

import logging
from typing import Any

from ..config import settings
from ..models.vector.qdrant_client import user_memory_store
from ..database.redis_client import cache

logger = logging.getLogger(__name__)

try:
    from mem0 import Memory
    _mem0_config = {
        "vector_store": {
            "provider": "qdrant",
            "config": {
                "host": settings.QDRANT_URL.replace("http://", "").split(":")[0],
                "port": int(settings.QDRANT_URL.split(":")[-1]),
                "collection_name": "mem0_user_memory",
                "embedding_model_dims": 3072,
            },
        },
        "embedder": {
            "provider": "openai",
            "config": {
                "api_key": settings.OPENAI_API_KEY,
                "model": "text-embedding-3-large",
            },
        },
        "llm": {
            "provider": "anthropic",
            "config": {
                "api_key": settings.ANTHROPIC_API_KEY,
                "model": "claude-haiku-4-5-20251001",
            },
        },
    }
    _mem0 = Memory.from_config(_mem0_config)
    HAS_MEM0 = True
except Exception as e:
    logger.warning(f"Mem0 not available: {e}. Using Qdrant directly.")
    _mem0 = None
    HAS_MEM0 = False


async def store_memory(user_id: str, content: str, metadata: dict | None = None) -> str:
    """Store a memory fact about the user."""
    if HAS_MEM0 and _mem0:
        try:
            result = _mem0.add(content, user_id=user_id, metadata=metadata or {})
            return result.get("id", "")
        except Exception as e:
            logger.error(f"Mem0 store failed: {e}")

    return await user_memory_store.store_qa(
        user_id=user_id,
        session_id="mem0_fallback",
        question=content,
        answer="",
        confidence=0,
        question_type="memory",
    )


async def retrieve_memories(user_id: str, query: str, limit: int = 5) -> list[dict[str, Any]]:
    """Retrieve relevant memories for a user given a query."""
    cache_key = f"mem:{user_id}:{hash(query) % 10000}"
    cached = await cache.get(cache_key)
    if cached:
        return cached

    memories: list[dict[str, Any]] = []

    if HAS_MEM0 and _mem0:
        try:
            results = _mem0.search(query, user_id=user_id, limit=limit)
            memories = [
                {"content": r.get("memory", ""), "score": r.get("score", 0.0)}
                for r in results.get("results", [])
            ]
        except Exception as e:
            logger.error(f"Mem0 search failed: {e}")

    if not memories:
        qdrant_results = await user_memory_store.retrieve_similar(
            user_id=user_id,
            question=query,
            limit=limit,
        )
        memories = [
            {
                "content": r["payload"].get("question", ""),
                "answer": r["payload"].get("answer", ""),
                "score": r["score"],
            }
            for r in qdrant_results
        ]

    await cache.set(cache_key, memories, ttl=300)
    return memories


async def get_user_weakness_summary(user_id: str) -> str:
    """Retrieve semantic summary of user's weak areas for context injection."""
    memories = await retrieve_memories(
        user_id=user_id,
        query="topics where this user struggled or made mistakes",
        limit=5,
    )

    if not memories:
        return "No previous session data available."

    weak_areas = [m.get("content", "") for m in memories if m.get("score", 0) > 0.7]
    return "Historically weak areas: " + "; ".join(weak_areas[:3]) if weak_areas else "No clear weak areas identified yet."
