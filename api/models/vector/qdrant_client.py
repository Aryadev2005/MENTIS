"""High-level Qdrant operations for MENTIS vector search."""

import logging
import uuid
from typing import Any

from ...database.qdrant_init import get_qdrant, upsert_vectors, search_similar
from .embeddings import embed_text, embed_with_cache

logger = logging.getLogger(__name__)


class QuestionVectorStore:
    """Manages question embeddings in Qdrant for RAG retrieval."""

    def __init__(self, collection: str):
        self.collection = collection

    async def upsert_question(
        self,
        question_text: str,
        answer_text: str,
        payload: dict[str, Any],
        question_id: str | None = None,
    ) -> str:
        qid = question_id or str(uuid.uuid4())
        embedding = await embed_text(question_text)

        await upsert_vectors(
            collection_name=self.collection,
            ids=[qid],
            vectors=[embedding],
            payloads=[{
                "question": question_text,
                "answer": answer_text,
                **payload,
            }],
        )
        return qid

    async def search(
        self,
        query: str,
        limit: int = 5,
        score_threshold: float = 0.72,
        filters: dict[str, Any] | None = None,
        cache: Any | None = None,
    ) -> list[dict[str, Any]]:
        embedding = await embed_with_cache(query, cache=cache)

        results = await search_similar(
            collection_name=self.collection,
            query_vector=embedding,
            limit=limit,
            score_threshold=score_threshold,
            filters=filters,
        )

        return results


class UserMemoryStore:
    """Manages per-user semantic memory in Qdrant."""

    COLLECTION = "user_memory"

    async def store_qa(
        self,
        user_id: str,
        session_id: str,
        question: str,
        answer: str,
        confidence: int,
        question_type: str,
        topic: str | None = None,
    ) -> str:
        memory_id = str(uuid.uuid4())
        embedding = await embed_text(question)

        await upsert_vectors(
            collection_name=self.COLLECTION,
            ids=[memory_id],
            vectors=[embedding],
            payloads=[{
                "user_id": user_id,
                "session_id": session_id,
                "question": question,
                "answer": answer,
                "confidence": confidence,
                "question_type": question_type,
                "topic": topic,
            }],
        )
        return memory_id

    async def retrieve_similar(
        self,
        user_id: str,
        question: str,
        limit: int = 3,
        cache: Any | None = None,
    ) -> list[dict[str, Any]]:
        return await search_similar(
            collection_name=self.COLLECTION,
            query_vector=await embed_with_cache(question, cache=cache),
            limit=limit,
            score_threshold=0.75,
            filters={"user_id": user_id},
        )


oa_question_store = QuestionVectorStore("oa_questions")
interview_question_store = QuestionVectorStore("interview_questions")
user_memory_store = UserMemoryStore()
