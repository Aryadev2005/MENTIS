"""Offline fallback AI service using local Ollama models."""

import asyncio
import json
import logging
from typing import AsyncIterator

import httpx

from ..config import settings

logger = logging.getLogger(__name__)

OLLAMA_BASE = getattr(settings, "OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = "llama3.2"
OLLAMA_FAST_MODEL = "llama3.2:1b"
CONNECT_TIMEOUT = 2.0


async def is_ollama_available() -> bool:
    try:
        async with httpx.AsyncClient(timeout=CONNECT_TIMEOUT) as client:
            response = await client.get(f"{OLLAMA_BASE}/api/tags")
            return response.status_code == 200
    except Exception:
        return False


async def _ensure_model(model: str) -> bool:
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{OLLAMA_BASE}/api/tags")
            tags = response.json()
            available = [m["name"] for m in tags.get("models", [])]
            return any(model in name for name in available)
    except Exception:
        return False


async def stream_answer_offline(
    question: str,
    context: str = "",
    system: str = "",
) -> AsyncIterator[str]:
    """Stream an answer from local Ollama when cloud AI is unavailable."""
    if not system:
        system = (
            "You are a helpful interview assistant for software engineering candidates. "
            "Give clear, structured answers. Be concise. Use STAR format for behavioral questions."
        )

    messages = []
    if context:
        messages.append({
            "role": "user",
            "content": f"Context:\n{context}\n\nQuestion: {question}",
        })
    else:
        messages.append({"role": "user", "content": question})

    payload = {
        "model": OLLAMA_MODEL,
        "messages": messages,
        "system": system,
        "stream": True,
        "options": {
            "temperature": 0.7,
            "num_predict": 512,
        },
    }

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream(
                "POST",
                f"{OLLAMA_BASE}/api/chat",
                json=payload,
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.strip():
                        continue
                    try:
                        data = json.loads(line)
                        token = data.get("message", {}).get("content", "")
                        if token:
                            yield token
                        if data.get("done"):
                            break
                    except json.JSONDecodeError:
                        continue
    except httpx.ConnectError:
        yield "[Offline mode: Ollama not running. Start Ollama for offline support.]"
    except Exception as e:
        logger.error("Ollama streaming error: %s", e)
        yield f"[Offline mode error: {type(e).__name__}]"


async def detect_question_offline(transcript: str) -> dict:
    """Detect if a transcript contains an interview question using Ollama."""
    prompt = (
        f'Analyze this transcript: "{transcript[:500]}"\n\n'
        'Reply ONLY with valid JSON:\n'
        '{"is_question": true/false, "question": "extracted question or null", '
        '"type": "behavioral/technical/situational/null"}'
    )

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{OLLAMA_BASE}/api/generate",
                json={
                    "model": OLLAMA_FAST_MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json",
                    "options": {"temperature": 0.1, "num_predict": 100},
                },
            )
            response.raise_for_status()
            text = response.json().get("response", "{}")
            return json.loads(text)
    except Exception:
        return {"is_question": False, "question": None, "type": None}


async def solve_oa_offline(question_text: str, question_type: str, department: str) -> dict:
    """Solve an OA question offline via Ollama."""
    system = (
        f"You are an expert at solving {department} engineering OA questions. "
        "Provide correct, concise answers. For coding: show code + complexity. "
        "For MCQ: state the answer and reason. Reply ONLY with valid JSON."
    )
    prompt = (
        f'Question type: {question_type}\nQuestion: {question_text}\n\n'
        'Reply ONLY with valid JSON:\n'
        '{"answer": "...", "explanation": "...", "code": null_or_string, '
        '"time_complexity": null_or_string, "confidence": 60}'
    )

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{OLLAMA_BASE}/api/generate",
                json={
                    "model": OLLAMA_MODEL,
                    "prompt": prompt,
                    "system": system,
                    "stream": False,
                    "format": "json",
                    "options": {"temperature": 0.3, "num_predict": 600},
                },
            )
            response.raise_for_status()
            data = json.loads(response.json().get("response", "{}"))
            data["offline_mode"] = True
            return data
    except Exception as e:
        logger.error("Ollama OA solve error: %s", e)
        return {
            "answer": "Unable to solve offline. Please check network connection.",
            "explanation": str(e),
            "code": None,
            "time_complexity": None,
            "confidence": 0,
            "offline_mode": True,
        }
