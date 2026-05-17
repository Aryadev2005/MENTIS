"""FastAPI router for user profile and onboarding endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File
from slowapi import Limiter
from slowapi.util import get_remote_address

from ..controllers.onboarding_controller import (
    handle_resume_upload,
    get_calibration_questions,
    score_calibration,
    complete_onboarding,
)
from ..models.schemas.user import (
    UserCreate,
    UserPublic,
    UserProfile,
    OnboardingStep1,
    OnboardingStep2,
    OnboardingStep3,
    OnboardingStep5,
    OnboardingStep6,
    OnboardingStep7,
    OnboardingStep8,
)
from ..database.postgres import get_db
from ..database.redis_client import cache
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


@router.post("/register", response_model=UserPublic)
@limiter.limit("5/minute")
async def register_user(
    request: Request,
    body: UserCreate,
    db: AsyncSession = Depends(get_db),
) -> UserPublic:
    """Register a new user (called after Clerk auth)."""
    from ..models.db.user import User
    from sqlalchemy import select

    stmt = select(User).where(User.clerk_id == body.clerk_id)
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()

    if existing:
        return UserPublic.model_validate(existing)

    user = User(
        clerk_id=body.clerk_id,
        email=body.email,
        name=body.name,
        phone=body.phone,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    return UserPublic.model_validate(user)


@router.get("/me", response_model=UserProfile)
async def get_my_profile(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> UserProfile:
    """Get current user's full profile."""
    user_id = request.headers.get("X-User-Id", "")
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    from ..models.db.user import User
    from sqlalchemy import select

    stmt = select(User).where(User.id == uuid.UUID(user_id))
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return UserProfile.model_validate(user)


@router.post("/onboarding/step/1")
@limiter.limit("10/minute")
async def onboarding_step1(
    request: Request,
    body: OnboardingStep1,
    db: AsyncSession = Depends(get_db),
) -> dict:
    user_id = request.headers.get("X-User-Id", "")
    from ..models.db.user import User
    from sqlalchemy import select

    stmt = select(User).where(User.id == uuid.UUID(user_id))
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if user:
        user.name = body.name
        user.phone = body.phone
        await db.commit()

    return {"step": 1, "status": "complete"}


@router.post("/onboarding/step/2")
async def onboarding_step2(
    request: Request,
    body: OnboardingStep2,
    db: AsyncSession = Depends(get_db),
) -> dict:
    user_id = request.headers.get("X-User-Id", "")
    from ..models.db.user import User
    from sqlalchemy import select

    stmt = select(User).where(User.id == uuid.UUID(user_id))
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if user:
        user.college = body.college
        user.graduation_year = body.graduation_year
        user.cgpa = body.cgpa
        await db.commit()

    return {"step": 2, "status": "complete"}


@router.post("/onboarding/step/3")
async def onboarding_step3(
    request: Request,
    body: OnboardingStep3,
    db: AsyncSession = Depends(get_db),
) -> dict:
    user_id = request.headers.get("X-User-Id", "")
    from ..models.db.user import User
    from sqlalchemy import select

    stmt = select(User).where(User.id == uuid.UUID(user_id))
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if user:
        user.department = body.department
        await db.commit()

    return {"step": 3, "status": "complete"}


@router.post("/onboarding/step/4/resume")
@limiter.limit("5/minute")
async def onboarding_step4_resume(
    request: Request,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Upload and parse resume."""
    user_id = request.headers.get("X-User-Id", "")
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    allowed_types = {
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/msword",
    }
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Only PDF and DOCX files are accepted")

    if file.size and file.size > 5 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large. Maximum 5MB.")

    file_bytes = await file.read()
    parsed = await handle_resume_upload(file_bytes, file.filename or "resume.pdf", user_id, db)

    return {"step": 4, "status": "complete", "parsed": parsed}


@router.post("/onboarding/step/5")
async def onboarding_step5(
    request: Request,
    body: OnboardingStep5,
    db: AsyncSession = Depends(get_db),
) -> dict:
    user_id = request.headers.get("X-User-Id", "")
    from ..models.db.user import User
    from sqlalchemy import select

    stmt = select(User).where(User.id == uuid.UUID(user_id))
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if user:
        user.target_companies = body.target_companies
        await db.commit()

    return {"step": 5, "status": "complete"}


@router.post("/onboarding/step/6")
async def onboarding_step6(
    request: Request,
    body: OnboardingStep6,
    db: AsyncSession = Depends(get_db),
) -> dict:
    user_id = request.headers.get("X-User-Id", "")
    from ..models.db.user import User
    from sqlalchemy import select

    stmt = select(User).where(User.id == uuid.UUID(user_id))
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if user:
        user.current_role = body.current_role
        await db.commit()

    return {"step": 6, "status": "complete"}


@router.post("/onboarding/step/7")
async def onboarding_step7(
    request: Request,
    body: OnboardingStep7,
    db: AsyncSession = Depends(get_db),
) -> dict:
    user_id = request.headers.get("X-User-Id", "")
    from ..models.db.user import User
    from sqlalchemy import select

    stmt = select(User).where(User.id == uuid.UUID(user_id))
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if user:
        user.preferred_language = body.preferred_language
        await db.commit()

    return {"step": 7, "status": "complete"}


@router.get("/onboarding/calibration/{department}")
async def get_calibration(department: str) -> dict:
    """Get 3 calibration questions for the department."""
    questions = await get_calibration_questions(department)
    sanitized = [{k: v for k, v in q.items() if k != "correct"} for q in questions]
    return {"department": department, "questions": sanitized}


@router.post("/onboarding/step/8/calibration")
async def onboarding_step8_calibration(
    request: Request,
    body: OnboardingStep8,
    db: AsyncSession = Depends(get_db),
) -> dict:
    user_id = request.headers.get("X-User-Id", "")
    department = request.headers.get("X-Department", "CSE")

    result = await score_calibration(
        [a.model_dump() for a in body.answers],
        department,
        user_id,
        db,
    )
    return {"step": 8, "status": "complete", **result}


@router.post("/onboarding/complete", response_model=UserProfile)
async def complete_user_onboarding(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> UserProfile:
    user_id = request.headers.get("X-User-Id", "")
    return await complete_onboarding(user_id, db)
