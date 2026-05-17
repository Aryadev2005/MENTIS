"""Redis client with pub/sub support for real-time streaming."""

import json
import logging
from typing import Any, AsyncIterator

import redis.asyncio as aioredis
from redis.asyncio import Redis

from ..config import settings

logger = logging.getLogger(__name__)

_redis: Redis | None = None


async def init_redis() -> None:
    global _redis

    _redis = aioredis.from_url(
        settings.REDIS_URL,
        encoding="utf-8",
        decode_responses=True,
        max_connections=20,
        retry_on_timeout=True,
        socket_connect_timeout=5,
        socket_timeout=5,
    )

    await _redis.ping()
    logger.info("Redis connected")


async def close_redis() -> None:
    global _redis
    if _redis:
        await _redis.aclose()
        _redis = None
        logger.info("Redis connection closed")


def get_redis() -> Redis:
    if not _redis:
        raise RuntimeError("Redis not initialized. Call init_redis() first.")
    return _redis


class RedisCache:
    """High-level cache operations with TTL management."""

    def __init__(self, prefix: str = "mentis"):
        self.prefix = prefix

    def _key(self, key: str) -> str:
        return f"{self.prefix}:{key}"

    async def get(self, key: str) -> Any | None:
        r = get_redis()
        value = await r.get(self._key(key))
        if value is None:
            return None
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return value

    async def set(self, key: str, value: Any, ttl: int = 3600) -> None:
        r = get_redis()
        serialized = json.dumps(value) if not isinstance(value, str) else value
        await r.setex(self._key(key), ttl, serialized)

    async def delete(self, key: str) -> None:
        r = get_redis()
        await r.delete(self._key(key))

    async def exists(self, key: str) -> bool:
        r = get_redis()
        return bool(await r.exists(self._key(key)))

    async def expire(self, key: str, ttl: int) -> None:
        r = get_redis()
        await r.expire(self._key(key), ttl)

    async def lpush(self, key: str, value: Any) -> None:
        r = get_redis()
        await r.lpush(self._key(key), json.dumps(value))

    async def lrange(self, key: str, start: int = 0, end: int = -1) -> list[Any]:
        r = get_redis()
        items = await r.lrange(self._key(key), start, end)
        return [json.loads(item) for item in items]

    async def ltrim(self, key: str, start: int, end: int) -> None:
        r = get_redis()
        await r.ltrim(self._key(key), start, end)


class RedisPubSub:
    """Pub/Sub for streaming answer tokens to Electron overlay."""

    @staticmethod
    async def publish(channel: str, message: Any) -> None:
        r = get_redis()
        payload = json.dumps(message) if not isinstance(message, str) else message
        await r.publish(channel, payload)

    @staticmethod
    async def subscribe(channel: str) -> AsyncIterator[Any]:
        r = get_redis()
        pubsub = r.pubsub()
        await pubsub.subscribe(channel)
        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    try:
                        yield json.loads(message["data"])
                    except json.JSONDecodeError:
                        yield message["data"]
        finally:
            await pubsub.unsubscribe(channel)
            await pubsub.aclose()


class SessionContext:
    """Manages per-session context in Redis (last N Q&A pairs)."""

    MAX_PAIRS = 10
    TTL = 14400  # 4 hours

    def __init__(self, session_id: str):
        self.cache = RedisCache(prefix=f"session:{session_id}")

    async def push_qa(self, question: str, answer: str, confidence: int) -> None:
        qa = {"question": question, "answer": answer, "confidence": confidence}
        await self.cache.lpush("qa_history", qa)
        await self.cache.ltrim("qa_history", 0, self.MAX_PAIRS - 1)
        await self.cache.expire("qa_history", self.TTL)

    async def get_recent_qa(self, n: int = 3) -> list[dict]:
        items = await self.cache.lrange("qa_history", 0, n - 1)
        return items

    async def clear(self) -> None:
        await self.cache.delete("qa_history")


cache = RedisCache()
pubsub = RedisPubSub()
