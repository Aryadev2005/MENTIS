"""Seed OA question bank with company + branch questions."""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from api.database.postgres import init_db, get_session
from api.models.db.question import Company

COMPANIES = [
    # Mass Recruiters
    {"name": "TCS", "category": "mass_recruiter", "oa_format": {
        "sections": [
            {"name": "Verbal", "count": 24, "duration_mins": 20},
            {"name": "Aptitude", "count": 26, "duration_mins": 40},
            {"name": "Reasoning", "count": 30, "duration_mins": 50},
            {"name": "Coding", "count": 1, "duration_mins": 20},
        ],
        "total_duration_mins": 90,
        "difficulty": "easy-medium",
        "pattern": "TCS NQT",
    }},
    {"name": "Infosys", "category": "mass_recruiter", "oa_format": {
        "sections": [
            {"name": "Aptitude", "count": 20, "duration_mins": 25},
            {"name": "Logical", "count": 15, "duration_mins": 25},
            {"name": "Verbal", "count": 20, "duration_mins": 20},
            {"name": "Coding", "count": 2, "duration_mins": 30},
        ],
        "total_duration_mins": 100,
        "difficulty": "medium",
        "pattern": "Infosys Sp/PP",
    }},
    {"name": "Wipro", "category": "mass_recruiter", "oa_format": {
        "sections": [
            {"name": "Aptitude", "count": 16, "duration_mins": 16},
            {"name": "English", "count": 18, "duration_mins": 18},
            {"name": "Online Test", "count": 20, "duration_mins": 20},
            {"name": "Coding", "count": 2, "duration_mins": 60},
            {"name": "Essay", "count": 1, "duration_mins": 20},
        ],
        "total_duration_mins": 134,
        "difficulty": "medium",
        "pattern": "WILP",
    }},
    {"name": "Accenture", "category": "mass_recruiter", "oa_format": {
        "sections": [
            {"name": "Cognitive Ability", "count": 50, "duration_mins": 50},
            {"name": "Technical Assessment", "count": 40, "duration_mins": 40},
            {"name": "Communication Assessment", "count": 1, "duration_mins": 30},
        ],
        "total_duration_mins": 120,
        "difficulty": "easy-medium",
        "pattern": "Accenture ABST",
    }},
    {"name": "Cognizant", "category": "mass_recruiter", "oa_format": {
        "sections": [
            {"name": "Aptitude", "count": 20, "duration_mins": 20},
            {"name": "Reasoning", "count": 20, "duration_mins": 20},
            {"name": "Verbal", "count": 25, "duration_mins": 25},
            {"name": "Coding", "count": 2, "duration_mins": 45},
        ],
        "total_duration_mins": 110,
        "difficulty": "medium",
    }},
    {"name": "HCL", "category": "mass_recruiter", "oa_format": {
        "sections": [
            {"name": "Aptitude", "count": 25, "duration_mins": 25},
            {"name": "Technical", "count": 25, "duration_mins": 25},
            {"name": "Coding", "count": 2, "duration_mins": 45},
        ],
        "total_duration_mins": 95,
        "difficulty": "easy-medium",
    }},

    # Product Companies
    {"name": "Amazon", "category": "product", "oa_format": {
        "sections": [
            {"name": "Coding", "count": 2, "duration_mins": 90},
            {"name": "Work Style", "count": 1, "duration_mins": 20},
        ],
        "total_duration_mins": 110,
        "difficulty": "hard",
        "pattern": "Amazon OA 2024",
        "notes": "Focus on DSA — Trees, DP, Graphs. LP questions based on Amazon's 16 principles.",
    }},
    {"name": "Google", "category": "product", "oa_format": {
        "sections": [
            {"name": "Coding", "count": 3, "duration_mins": 75},
        ],
        "total_duration_mins": 75,
        "difficulty": "hard",
        "pattern": "Kickstart/OA",
        "notes": "Algorithmic problems. Focus on time/space complexity optimization.",
    }},
    {"name": "Microsoft", "category": "product", "oa_format": {
        "sections": [
            {"name": "Coding", "count": 3, "duration_mins": 90},
            {"name": "Technical MCQ", "count": 15, "duration_mins": 20},
        ],
        "total_duration_mins": 110,
        "difficulty": "hard",
        "pattern": "MSVP OA",
    }},
    {"name": "Flipkart", "category": "product", "oa_format": {
        "sections": [
            {"name": "Aptitude", "count": 20, "duration_mins": 30},
            {"name": "Coding", "count": 2, "duration_mins": 90},
        ],
        "total_duration_mins": 120,
        "difficulty": "hard",
        "notes": "Hackerearth platform. Focus on DP and Graphs.",
    }},
    {"name": "Razorpay", "category": "product", "oa_format": {
        "sections": [
            {"name": "Coding", "count": 2, "duration_mins": 60},
            {"name": "System Design MCQ", "count": 10, "duration_mins": 20},
        ],
        "total_duration_mins": 80,
        "difficulty": "hard",
    }},
    {"name": "CRED", "category": "product", "oa_format": {
        "sections": [
            {"name": "Coding", "count": 2, "duration_mins": 90},
        ],
        "total_duration_mins": 90,
        "difficulty": "hard",
    }},
    {"name": "Zepto", "category": "product", "oa_format": {
        "sections": [
            {"name": "Coding", "count": 2, "duration_mins": 60},
            {"name": "Aptitude", "count": 15, "duration_mins": 20},
        ],
        "total_duration_mins": 80,
        "difficulty": "medium-hard",
    }},
    {"name": "PhonePe", "category": "product", "oa_format": {
        "sections": [
            {"name": "Coding", "count": 3, "duration_mins": 90},
        ],
        "total_duration_mins": 90,
        "difficulty": "hard",
    }},

    # Core Engineering
    {"name": "L&T", "category": "core_engineering", "oa_format": {
        "sections": [
            {"name": "Aptitude", "count": 20, "duration_mins": 20},
            {"name": "Technical - Thermodynamics", "count": 10, "duration_mins": 15},
            {"name": "Technical - Fluid Mechanics", "count": 10, "duration_mins": 15},
            {"name": "Technical - Manufacturing", "count": 10, "duration_mins": 15},
        ],
        "total_duration_mins": 65,
        "difficulty": "medium",
        "notes": "Mech/Civil focus. Company values safety and project management.",
    }},
    {"name": "Tata Motors", "category": "core_engineering", "oa_format": {
        "sections": [
            {"name": "Aptitude", "count": 25, "duration_mins": 25},
            {"name": "Mechanical Technical", "count": 30, "duration_mins": 30},
            {"name": "HR Questions", "count": 10, "duration_mins": 10},
        ],
        "total_duration_mins": 65,
        "difficulty": "medium",
    }},
    {"name": "DRDO", "category": "core_engineering", "oa_format": {
        "sections": [
            {"name": "General Science", "count": 50, "duration_mins": 30},
            {"name": "Mathematics", "count": 50, "duration_mins": 45},
            {"name": "Domain Technical", "count": 100, "duration_mins": 60},
            {"name": "General English", "count": 50, "duration_mins": 25},
        ],
        "total_duration_mins": 160,
        "difficulty": "hard",
        "pattern": "DRDO CEPTAM",
    }},
    {"name": "ISRO", "category": "core_engineering", "oa_format": {
        "sections": [
            {"name": "Technical", "count": 80, "duration_mins": 90},
        ],
        "total_duration_mins": 90,
        "difficulty": "very-hard",
        "notes": "GATE-level questions. Focus on fundamentals.",
    }},

    # Consulting/Finance
    {"name": "Deloitte", "category": "consulting_finance", "oa_format": {
        "sections": [
            {"name": "Verbal Reasoning", "count": 30, "duration_mins": 25},
            {"name": "Numerical Reasoning", "count": 20, "duration_mins": 25},
            {"name": "Logical Reasoning", "count": 20, "duration_mins": 20},
            {"name": "Situational Judgement", "count": 20, "duration_mins": 30},
        ],
        "total_duration_mins": 100,
        "difficulty": "medium",
        "pattern": "Deloitte SOVA",
    }},
    {"name": "Goldman Sachs", "category": "consulting_finance", "oa_format": {
        "sections": [
            {"name": "Coding", "count": 2, "duration_mins": 60},
            {"name": "Quantitative", "count": 20, "duration_mins": 30},
        ],
        "total_duration_mins": 90,
        "difficulty": "very-hard",
        "notes": "One of the hardest OAs. Focus on advanced DS&A and probability.",
    }},
]


async def seed_companies() -> None:
    await init_db()

    async for session in get_session():
        from sqlalchemy import select

        for company_data in COMPANIES:
            stmt = select(Company).where(Company.name == company_data["name"])
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()

            if not existing:
                company = Company(
                    name=company_data["name"],
                    category=company_data["category"],
                    oa_format=company_data.get("oa_format"),
                    typical_questions=[],
                    student_reports=[],
                )
                session.add(company)

        await session.commit()
        print(f"✓ Seeded {len(COMPANIES)} companies")
        break


if __name__ == "__main__":
    asyncio.run(seed_companies())
