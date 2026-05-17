"""Bulk embed questions from PostgreSQL into Qdrant for RAG retrieval."""

import asyncio
import sys
import os
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from api.database.postgres import init_db, get_session
from api.database.qdrant_init import init_qdrant
from api.database.redis_client import init_redis
from api.models.db.question import Question
from api.models.vector.embeddings import embed_batch
from api.database.qdrant_init import upsert_vectors
from sqlalchemy import select


async def embed_all_questions(batch_size: int = 50) -> None:
    await init_db()
    await init_qdrant()
    await init_redis()

    async for session in get_session():
        stmt = select(Question).where(
            Question.question_embedding.is_(None),
            Question.question_text.isnot(None),
        )
        result = await session.execute(stmt)
        questions = result.scalars().all()

        print(f"Found {len(questions)} unembedded questions")

        for i in range(0, len(questions), batch_size):
            batch = questions[i : i + batch_size]
            texts = [q.question_text for q in batch]

            print(f"Embedding batch {i // batch_size + 1} ({len(batch)} questions)...")
            embeddings = await embed_batch(texts)

            ids = []
            vectors = []
            payloads = []

            for q, emb in zip(batch, embeddings):
                q.question_embedding = emb

                ids.append(str(q.id or uuid.uuid4()))
                vectors.append(emb)
                payloads.append({
                    "question": q.question_text,
                    "answer": q.answer_text or "",
                    "question_type": q.question_type,
                    "company": q.company or "",
                    "department": q.department or "",
                    "difficulty": q.difficulty or "medium",
                    "topic": q.topic or "",
                    "verified": q.is_verified,
                    "solve_count": q.solve_count,
                })

            collection = "oa_questions" if q.question_type and "mcq" in q.question_type else "interview_questions"
            await upsert_vectors(collection, ids, vectors, payloads)

            await session.commit()
            print(f"  ✓ Batch {i // batch_size + 1} embedded and upserted to Qdrant")

        print("✓ All questions embedded!")
        break


if __name__ == "__main__":
    asyncio.run(embed_all_questions())
