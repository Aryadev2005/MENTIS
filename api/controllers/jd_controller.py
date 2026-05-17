"""JD (Job Description) parsing controller — extracts key competencies."""

import json
import logging
from typing import Any

import anthropic
from ..config import settings

logger = logging.getLogger(__name__)

JD_EXTRACTION_PROMPT = """
Extract key competencies from this job description. Output ONLY valid JSON:
{
  "technical": ["list of technical skills, technologies, frameworks mentioned"],
  "behavioral": ["list of soft skills, behavioral traits, leadership qualities"],
  "domain": ["list of domain-specific knowledge areas"],
  "summary": "2-sentence summary of what this role prioritizes"
}

Be concise. Max 8 items per category.
"""


async def extract_jd_keywords(jd_text: str) -> dict[str, Any]:
    """Extract structured keywords from a job description."""
    client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    response = await client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=512,
        system=JD_EXTRACTION_PROMPT,
        messages=[{"role": "user", "content": jd_text[:4000]}],
    )

    text = response.content[0].text.strip()
    if text.startswith("```"):
        text = text.split("```")[1].replace("json", "").strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        logger.warning("JD extraction JSON parse failed, returning empty")
        return {"technical": [], "behavioral": [], "domain": [], "summary": ""}
