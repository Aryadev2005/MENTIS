"""OpenAI service — vision OCR for OA screenshots and code generation fallback."""

import logging
import json
from typing import AsyncIterator

from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import openai

from ..config import settings

logger = logging.getLogger(__name__)

VISION_MODEL = "gpt-4o"
FAST_MODEL = "gpt-4o-mini"

_client: AsyncOpenAI | None = None


def get_client() -> AsyncOpenAI:
    global _client
    if not _client:
        _client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    return _client


OA_PARSE_PROMPT = """
Extract the complete question from this OA/exam screenshot with 100% accuracy.

Output ONLY a JSON object with this exact structure:
{
  "question_text": "The complete question text",
  "question_type": "coding|mcq_aptitude|mcq_technical_cs|mcq_technical_ece|mcq_technical_mech|mcq_technical_civil|mcq_technical_chem|debugging|output_prediction",
  "options": ["A", "B", "C", "D"] or null,
  "code_snippet": "code if present" or null,
  "constraints": "constraints if present" or null,
  "examples": "input/output examples if present" or null,
  "language_hint": "C++|Python|Java" or null
}

Rules:
- question_type must be one of the exact strings listed
- options must be an array of 4 strings for MCQ, or null for other types
- Preserve ALL mathematical notation exactly
- Do not interpret or solve — only extract
"""


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=8),
    retry=retry_if_exception_type((openai.APIConnectionError, openai.RateLimitError)),
    reraise=True,
)
async def parse_oa_screenshot(screenshot_b64: str) -> dict:
    """Extract question from OA screenshot using GPT-4o Vision."""
    client = get_client()

    response = await client.chat.completions.create(
        model=VISION_MODEL,
        max_tokens=1024,
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{screenshot_b64}",
                        "detail": "high",
                    },
                },
                {
                    "type": "text",
                    "text": OA_PARSE_PROMPT,
                },
            ],
        }],
        response_format={"type": "json_object"},
    )

    text = response.choices[0].message.content or "{}"
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        logger.error(f"GPT-4o Vision parse failed: {e}\nRaw: {text[:500]}")
        return {}


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=8),
    reraise=True,
)
async def generate_code(
    problem: str,
    language: str = "Python",
    context: str = "",
) -> str:
    """Generate complete working code for a coding problem."""
    client = get_client()

    system = (
        f"You are an expert competitive programmer. Write clean, correct, well-commented {language} code. "
        "Always include: time/space complexity, edge case handling. No incomplete solutions."
    )

    user_content = problem
    if context:
        user_content = f"SIMILAR PROBLEM FOR REFERENCE:\n{context}\n\nPROBLEM TO SOLVE:\n{problem}"

    response = await client.chat.completions.create(
        model=VISION_MODEL,
        max_tokens=2048,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user_content},
        ],
        temperature=0.1,
    )

    return response.choices[0].message.content or ""


async def stream_oa_solution(prompt: str, system: str) -> AsyncIterator[str]:
    """Stream OA solution tokens from GPT-4o."""
    client = get_client()

    stream = await client.chat.completions.create(
        model=VISION_MODEL,
        max_tokens=1500,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        stream=True,
        temperature=0.1,
    )

    async for chunk in stream:
        delta = chunk.choices[0].delta.content
        if delta:
            yield delta
