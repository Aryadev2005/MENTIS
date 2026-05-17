"""Resume parsing service — PDF/DOCX → structured knowledge via LLM."""

import io
import json
import logging
from pathlib import Path
from typing import BinaryIO

import anthropic

try:
    import fitz  # PyMuPDF
    HAS_PYMUPDF = True
except ImportError:
    HAS_PYMUPDF = False

try:
    from docx import Document
    HAS_DOCX = True
except ImportError:
    HAS_DOCX = False

from ..config import settings

logger = logging.getLogger(__name__)

RESUME_EXTRACTION_PROMPT = """
Extract all information from this resume into a JSON object with EXACTLY this structure.
Be precise — only include information explicitly stated in the resume.
Do NOT invent or infer skills not mentioned.

{
  "name": "string",
  "email": "string",
  "phone": "string or null",
  "college": "string or null",
  "graduation_year": integer or null,
  "cgpa": float or null,
  "department": "CSE|ECE|Mechanical|Civil|Chemical|EEE|Other or null",
  "skills": [
    {"skill": "string", "proficiency_level": "beginner|intermediate|advanced", "years": float or null}
  ],
  "experiences": [
    {
      "company": "string",
      "role": "string",
      "duration": "string",
      "duration_months": integer or null,
      "achievements": ["string"]
    }
  ],
  "projects": [
    {
      "name": "string",
      "tech_stack": ["string"],
      "description": "string",
      "impact": "string or null"
    }
  ],
  "certifications": [
    {"name": "string", "issuer": "string or null", "year": integer or null}
  ],
  "achievements": ["string"]
}
"""


def extract_text_from_pdf(file_bytes: bytes) -> str:
    if not HAS_PYMUPDF:
        raise ImportError("PyMuPDF not installed. Run: pip install pymupdf")

    doc = fitz.open(stream=file_bytes, filetype="pdf")
    pages_text = []
    for page in doc:
        pages_text.append(page.get_text("text"))
    doc.close()
    return "\n".join(pages_text)


def extract_text_from_docx(file_bytes: bytes) -> str:
    if not HAS_DOCX:
        raise ImportError("python-docx not installed. Run: pip install python-docx")

    doc = Document(io.BytesIO(file_bytes))
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    return "\n".join(paragraphs)


async def parse_resume(file_bytes: bytes, filename: str) -> dict:
    """Parse resume file → structured dict using Claude."""
    suffix = Path(filename).suffix.lower()

    if suffix == ".pdf":
        raw_text = extract_text_from_pdf(file_bytes)
    elif suffix in (".docx", ".doc"):
        raw_text = extract_text_from_docx(file_bytes)
    else:
        raise ValueError(f"Unsupported file format: {suffix}. Use PDF or DOCX.")

    if len(raw_text.strip()) < 100:
        raise ValueError("Resume appears to be empty or unreadable.")

    raw_text = raw_text[:12000]

    client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
    response = await client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2048,
        system=RESUME_EXTRACTION_PROMPT,
        messages=[{
            "role": "user",
            "content": f"RESUME TEXT:\n{raw_text}"
        }],
    )

    text = response.content[0].text.strip()
    if text.startswith("```"):
        text = text.split("```")[1].replace("json", "").strip()

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as e:
        logger.error(f"Resume parse JSON error: {e}\nRaw: {text[:500]}")
        raise ValueError("Could not parse resume. Please try a different file.")

    skill_summary = await generate_skill_summary(parsed)
    parsed["skill_summary"] = skill_summary

    return parsed


async def generate_skill_summary(parsed_resume: dict) -> str:
    """Generate 200-word skill summary paragraph for LLM context injection."""
    client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    name = parsed_resume.get("name", "The candidate")
    skills = ", ".join([s["skill"] for s in parsed_resume.get("skills", [])[:15]])
    experiences = "; ".join([
        f"{e['role']} at {e['company']}" for e in parsed_resume.get("experiences", [])[:3]
    ])
    projects = "; ".join([p["name"] for p in parsed_resume.get("projects", [])[:3]])
    dept = parsed_resume.get("department", "Engineering")
    college = parsed_resume.get("college", "")

    response = await client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=350,
        system=(
            "Write a concise 200-word professional summary of this candidate's skills and experience. "
            "Use third person. Focus on technical strengths. Do not invent or exaggerate anything."
        ),
        messages=[{
            "role": "user",
            "content": (
                f"Name: {name}\nDepartment: {dept}\nCollege: {college}\n"
                f"Skills: {skills}\nExperience: {experiences}\nProjects: {projects}"
            )
        }],
    )

    return response.content[0].text.strip()
