"""FastAPI router for OA solver endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Request, WebSocket, WebSocketDisconnect
from slowapi import Limiter
from slowapi.util import get_remote_address

from ..controllers.oa_controller import (
    capture_and_solve,
    solve_oa_question,
    contribute_question,
    get_company_oa_brief,
)
from ..models.schemas.oa import (
    OACaptureRequest,
    OASolveRequest,
    OASolution,
    OAContributeRequest,
)
from ..database.redis_client import cache
from ..services.group_oa_service import group_oa_service

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


@router.post("/capture", response_model=OASolution)
@limiter.limit("20/minute")
async def capture_and_solve_oa(
    request: Request,
    body: OACaptureRequest,
) -> OASolution:
    """Full OA pipeline: screenshot → parse → solve. Returns complete solution."""
    user_context = {
        "user_id": body.user_id,
        "department": body.department,
        "preferred_language": request.headers.get("X-Preferred-Language", "Python"),
    }

    if not body.screenshot_b64:
        raise HTTPException(status_code=400, detail="Screenshot data required")

    return await capture_and_solve(body, user_context)


@router.post("/solve", response_model=OASolution)
@limiter.limit("30/minute")
async def solve_parsed_question(
    request: Request,
    body: OASolveRequest,
) -> OASolution:
    """Solve an already-parsed OA question (skips screenshot parsing)."""
    user_context = {
        "user_id": body.user_id,
        "department": body.department,
        "preferred_language": body.preferred_language,
    }
    return await solve_oa_question(body, user_context)


@router.post("/contribute")
@limiter.limit("50/minute")
async def contribute_oa_question(
    request: Request,
    body: OAContributeRequest,
) -> dict:
    """Contribute a verified OA question to the shared bank."""
    question_id = await contribute_question(body)
    return {
        "status": "ok",
        "question_id": question_id,
        "message": "Thank you! Your contribution helps future students.",
    }


@router.get("/brief/{company}/{department}")
async def get_oa_brief(company: str, department: str) -> dict:
    """Get pre-session OA brief for a company + department."""
    return await get_company_oa_brief(company, department)


@router.websocket("/group/{group_code}")
async def group_oa_session(websocket: WebSocket, group_code: str) -> None:
    """WebSocket endpoint for Group OA Mode — encrypted, up to 6 students, 3h TTL."""
    user_id = websocket.headers.get("X-User-Id", f"anon-{id(websocket)}")
    await group_oa_service.handle_connection(group_code, user_id, websocket)


@router.get("/group/active")
async def list_active_groups() -> dict:
    """List all currently active group OA sessions."""
    return {"groups": group_oa_service.get_active_groups()}
