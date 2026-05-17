"""Embedding generation using OpenAI text-embedding-3-large."""

import asyncio
import hashlib
import logging
from functools import lru_cache
from typing import Any

from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from ...config import settings

logger = logging.getLogger(__name__)

EMBEDDING_MODEL = "text-embedding-3-large"
EMBEDDING_DIM = 3072

_openai_client: AsyncOpenAI | None = None


def get_openai_client() -> AsyncOpenAI:
    global _openai_client
    if not _openai_client:
        _openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    return _openai_client


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    reraise=True,
)
async def embed_text(text: str) -> list[float]:
    """Embed a single text string. Retries 3x with exponential backoff."""
    client = get_openai_client()

    clean_text = text.strip().replace("\n", " ")[:8000]

    response = await client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=clean_text,
        dimensions=EMBEDDING_DIM,
    )
    return response.data[0].embedding


async def embed_batch(texts: list[str], batch_size: int = 20) -> list[list[float]]:
    """Embed multiple texts in batches."""
    all_embeddings: list[list[float]] = []

    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        client = get_openai_client()

        clean_batch = [t.strip().replace("\n", " ")[:8000] for t in batch]

        response = await client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=clean_batch,
            dimensions=EMBEDDING_DIM,
        )
        embeddings = [item.embedding for item in sorted(response.data, key=lambda x: x.index)]
        all_embeddings.extend(embeddings)

    return all_embeddings


def text_to_cache_key(text: str) -> str:
    """Deterministic hash of text for Redis cache key."""
    normalized = text.strip().lower()
    return hashlib.sha256(normalized.encode()).hexdigest()[:16]


async def embed_with_cache(
    text: str,
    cache: Any | None = None,
    ttl: int = 86400 * 7,
) -> list[float]:
    """Embed with Redis cache layer — avoids re-embedding identical questions."""
    if cache is not None:
        cache_key = f"embed:{text_to_cache_key(text)}"
        cached = await cache.get(cache_key)
        if cached:
            return cached

    embedding = await embed_text(text)

    if cache is not None:
        await cache.set(cache_key, embedding, ttl=ttl)

    return embedding
