"""Qdrant vector database initialization and collection management."""

import logging
from typing import Any

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    HnswConfigDiff,
    OptimizersConfigDiff,
    QuantizationConfig,
    ScalarQuantization,
    ScalarType,
    PayloadSchemaType,
    TokenizerType,
    TextIndexParams,
)

from ..config import settings

logger = logging.getLogger(__name__)

_qdrant_client: AsyncQdrantClient | None = None

EMBEDDING_DIM = 3072

COLLECTIONS = {
    "oa_questions": {
        "description": "OA question bank — all branches, all companies",
        "vector_size": EMBEDDING_DIM,
    },
    "interview_questions": {
        "description": "Interview Q&A pairs — behavioural, technical, HR",
        "vector_size": EMBEDDING_DIM,
    },
    "user_memory": {
        "description": "Per-user semantic memory — past Q&As and learning history",
        "vector_size": EMBEDDING_DIM,
    },
}


def get_qdrant() -> AsyncQdrantClient:
    if not _qdrant_client:
        raise RuntimeError("Qdrant not initialized. Call init_qdrant() first.")
    return _qdrant_client


async def init_qdrant() -> None:
    global _qdrant_client

    _qdrant_client = AsyncQdrantClient(
        url=settings.QDRANT_URL,
        api_key=settings.QDRANT_API_KEY or None,
        timeout=30,
    )

    await _qdrant_client.get_collections()

    for name, config in COLLECTIONS.items():
        await _ensure_collection(name, config["vector_size"])

    logger.info(f"Qdrant initialized with {len(COLLECTIONS)} collections")


async def _ensure_collection(name: str, vector_size: int) -> None:
    client = get_qdrant()

    existing = await client.get_collections()
    collection_names = {c.name for c in existing.collections}

    if name not in collection_names:
        await client.create_collection(
            collection_name=name,
            vectors_config=VectorParams(
                size=vector_size,
                distance=Distance.COSINE,
                on_disk=False,
            ),
            hnsw_config=HnswConfigDiff(
                m=16,
                ef_construct=200,
                full_scan_threshold=10000,
            ),
            optimizers_config=OptimizersConfigDiff(
                default_segment_number=2,
                max_segment_size=50000,
                memmap_threshold=20000,
            ),
            quantization_config=QuantizationConfig(
                scalar=ScalarQuantization(
                    type=ScalarType.INT8,
                    quantile=0.99,
                    always_ram=True,
                )
            ),
        )
        logger.info(f"Qdrant collection created: {name}")
    else:
        logger.debug(f"Qdrant collection already exists: {name}")

    await _create_payload_indexes(name)


async def _create_payload_indexes(collection_name: str) -> None:
    client = get_qdrant()

    shared_indexes: dict[str, Any] = {
        "company": PayloadSchemaType.KEYWORD,
        "department": PayloadSchemaType.KEYWORD,
        "question_type": PayloadSchemaType.KEYWORD,
        "difficulty": PayloadSchemaType.KEYWORD,
        "created_at": PayloadSchemaType.DATETIME,
    }

    collection_specific: dict[str, dict[str, Any]] = {
        "user_memory": {
            "user_id": PayloadSchemaType.KEYWORD,
            "session_id": PayloadSchemaType.KEYWORD,
            "confidence": PayloadSchemaType.FLOAT,
        },
        "oa_questions": {
            "verified": PayloadSchemaType.BOOL,
            "solve_count": PayloadSchemaType.INTEGER,
        },
        "interview_questions": {
            "question_category": PayloadSchemaType.KEYWORD,
        },
    }

    indexes = {**shared_indexes, **collection_specific.get(collection_name, {})}

    for field_name, field_type in indexes.items():
        try:
            await client.create_payload_index(
                collection_name=collection_name,
                field_name=field_name,
                field_schema=field_type,
            )
        except Exception:
            pass


async def upsert_vectors(
    collection_name: str,
    ids: list[str],
    vectors: list[list[float]],
    payloads: list[dict[str, Any]],
) -> None:
    from qdrant_client.models import PointStruct

    client = get_qdrant()
    points = [
        PointStruct(id=pid, vector=vec, payload=payload)
        for pid, vec, payload in zip(ids, vectors, payloads)
    ]
    await client.upsert(collection_name=collection_name, points=points)


async def search_similar(
    collection_name: str,
    query_vector: list[float],
    limit: int = 5,
    score_threshold: float = 0.7,
    filters: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    from qdrant_client.models import Filter, FieldCondition, MatchValue

    client = get_qdrant()

    qdrant_filter = None
    if filters:
        conditions = [
            FieldCondition(key=k, match=MatchValue(value=v))
            for k, v in filters.items()
        ]
        qdrant_filter = Filter(must=conditions)

    results = await client.search(
        collection_name=collection_name,
        query_vector=query_vector,
        limit=limit,
        score_threshold=score_threshold,
        query_filter=qdrant_filter,
        with_payload=True,
    )

    return [
        {
            "id": str(r.id),
            "score": r.score,
            "payload": r.payload or {},
        }
        for r in results
    ]
