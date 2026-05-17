"""FastAPI router for analytics and performance data."""

from fastapi import APIRouter, Depends, HTTPException, Request
from ..controllers.analytics_controller import (
    get_skill_radar,
    get_company_readiness,
    get_session_heatmap,
    get_improvement_trend,
)
from ..database.postgres import get_db
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


@router.get("/radar/{department}")
async def skill_radar(
    request: Request,
    department: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get 8-dimension skill radar for user's department."""
    user_id = request.headers.get("X-User-Id", "")
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")
    return await get_skill_radar(user_id, department, db)


@router.get("/readiness/{company}")
async def company_readiness(
    request: Request,
    company: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get company readiness score."""
    user_id = request.headers.get("X-User-Id", "")
    department = request.headers.get("X-Department", "CSE")
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")
    return await get_company_readiness(user_id, company, department, db)


@router.get("/heatmap")
async def session_heatmap(
    request: Request,
    days: int = 90,
    db: AsyncSession = Depends(get_db),
) -> list:
    """Get session calendar heatmap."""
    user_id = request.headers.get("X-User-Id", "")
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")
    return await get_session_heatmap(user_id, days, db)


@router.get("/trend")
async def improvement_trend(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> list:
    """Get answer quality improvement over time."""
    user_id = request.headers.get("X-User-Id", "")
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")
    return await get_improvement_trend(user_id, db)
