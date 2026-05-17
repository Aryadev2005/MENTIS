"""Anthropic Claude service — streaming answers with retry logic."""

import logging
import time
from typing import AsyncIterator

import anthropic
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from ..config import settings

logger = logging.getLogger(__name__)

PRIMARY_MODEL = "claude-sonnet-4-20250514"
FAST_MODEL = "claude-haiku-4-5-20251001"

_client: anthropic.AsyncAnthropic | None = None


def get_client() -> anthropic.AsyncAnthropic:
    global _client
    if not _client:
        _client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
    return _client


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=8),
    retry=retry_if_exception_type((anthropic.APIConnectionError, anthropic.RateLimitError)),
    reraise=True,
)
async def detect_question(transcript: str) -> dict:
    """Fast non-streaming call to detect if transcript contains a question."""
    client = get_client()
    start = time.perf_counter()

    response = await client.messages.create(
        model=FAST_MODEL,
        max_tokens=256,
        system=(
            "You are a question detector. Given a transcript fragment, determine if it contains "
            "an interview/OA question. Output ONLY valid JSON matching this schema exactly: "
            '{"is_question": bool, "question": "string or null", '
            '"type": "behavioral|technical|hr|coding|null"}'
        ),
        messages=[{"role": "user", "content": f"Transcript: {transcript[:1500]}"}],
    )

    elapsed = round((time.perf_counter() - start) * 1000)
    logger.debug(f"Question detection: {elapsed}ms")

    import json
    try:
        text = response.content[0].text.strip()
        if text.startswith("```"):
            text = text.split("```")[1].replace("json", "").strip()
        return json.loads(text)
    except (json.JSONDecodeError, IndexError, KeyError) as e:
        logger.error(f"Failed to parse question detection response: {e}")
        return {"is_question": False, "question": None, "type": None}


async def stream_answer(
    question: str,
    system_prompt: str,
    context: str = "",
    model: str = PRIMARY_MODEL,
    max_tokens: int = 512,
) -> AsyncIterator[str]:
    """Stream interview answer tokens via Claude."""
    client = get_client()

    user_content = question
    if context:
        user_content = f"RELEVANT CONTEXT:\n{context}\n\nQUESTION: {question}"

    async with client.messages.stream(
        model=model,
        max_tokens=max_tokens,
        system=system_prompt,
        messages=[{"role": "user", "content": user_content}],
    ) as stream:
        async for text in stream.text_stream:
            yield text


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=8),
    reraise=True,
)
async def score_answer(question: str, answer: str) -> int:
    """Score an answer's quality 0-100. Fast non-streaming call."""
    client = get_client()

    response = await client.messages.create(
        model=FAST_MODEL,
        max_tokens=64,
        system=(
            "You are an interview coach evaluating answer quality. "
            "Score 0-100 based on: relevance, specificity, structure, confidence. "
            "Output ONLY a JSON object: {\"score\": <integer 0-100>}"
        ),
        messages=[{
            "role": "user",
            "content": f"Question: {question[:500]}\nAnswer: {answer[:1000]}"
        }],
    )

    import json
    try:
        text = response.content[0].text.strip()
        data = json.loads(text)
        return int(data.get("score", 70))
    except Exception:
        return 70


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=8),
    reraise=True,
)
async def solve_with_vision(screenshot_b64: str, parse_prompt: str) -> dict:
    """Extract question from screenshot using Claude Vision."""
    client = get_client()

    import json
    response = await client.messages.create(
        model=PRIMARY_MODEL,
        max_tokens=1024,
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/png",
                        "data": screenshot_b64,
                    },
                },
                {
                    "type": "text",
                    "text": parse_prompt,
                },
            ],
        }],
    )

    try:
        text = response.content[0].text.strip()
        if text.startswith("```"):
            text = text.split("```")[1].replace("json", "").strip()
        return json.loads(text)
    except (json.JSONDecodeError, IndexError, KeyError) as e:
        logger.error(f"Vision parse failed: {e}")
        return {}


async def generate_session_debrief(
    qa_pairs: list[dict],
    user_name: str,
    company: str,
) -> str:
    """Generate a post-session debrief paragraph."""
    client = get_client()

    qa_summary = "\n".join(
        [f"Q: {qa['question'][:200]}\nA quality: {qa.get('confidence', 70)}%" for qa in qa_pairs[:10]]
    )

    response = await client.messages.create(
        model=FAST_MODEL,
        max_tokens=400,
        system=(
            "You are a career coach. Generate a concise, actionable post-session debrief "
            "for an interview candidate. Identify weak areas and give specific recommendations. "
            "Keep it under 200 words. Be direct, supportive, and India-context-aware."
        ),
        messages=[{
            "role": "user",
            "content": (
                f"Student: {user_name}\nCompany targeted: {company}\n"
                f"Session Q&A performance:\n{qa_summary}"
            )
        }],
    )

    return response.content[0].text.strip()
