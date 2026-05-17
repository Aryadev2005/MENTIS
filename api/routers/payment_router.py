"""Razorpay payment endpoints."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ..database.postgres import get_db
from ..middleware.auth import get_current_user
from ..services import razorpay_service
from ..config import settings

logger = logging.getLogger(__name__)
router = APIRouter()


class CreateOrderRequest(BaseModel):
    plan: str


class VerifyPaymentRequest(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str
    plan: str


@router.post("/create-order")
async def create_order(
    body: CreateOrderRequest,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Create a Razorpay order for the given plan."""
    user_id = user.get("sub", "")
    if not user_id:
        raise HTTPException(status_code=401, detail="User ID missing from token")

    try:
        order = await razorpay_service.create_order(
            plan=body.plan,
            user_id=user_id,
        )
        return {
            "order_id": order["id"],
            "amount": order["amount"],
            "currency": order["currency"],
            "key_id": settings.RAZORPAY_KEY_ID,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Order creation failed: %s", e)
        raise HTTPException(status_code=500, detail="Payment service unavailable")


@router.post("/verify")
async def verify_payment(
    body: VerifyPaymentRequest,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Verify payment signature and upgrade user plan."""
    is_valid = razorpay_service.verify_payment_signature(
        order_id=body.razorpay_order_id,
        payment_id=body.razorpay_payment_id,
        signature=body.razorpay_signature,
    )

    if not is_valid:
        raise HTTPException(status_code=400, detail="Payment signature verification failed")

    user_id = user.get("sub", "")
    try:
        from ..models.db.user import User
        from sqlalchemy import select

        stmt = select(User).where(User.clerk_id == user_id)
        result = await db.execute(stmt)
        db_user = result.scalar_one_or_none()

        if db_user:
            db_user.plan = body.plan
            await db.commit()

        return {
            "status": "success",
            "plan": body.plan,
            "payment_id": body.razorpay_payment_id,
        }
    except Exception as e:
        logger.error("Plan upgrade failed: %s", e)
        raise HTTPException(status_code=500, detail="Failed to upgrade plan")


@router.post("/webhook")
async def razorpay_webhook(request: Request, db: AsyncSession = Depends(get_db)) -> dict:
    """Handle Razorpay webhook events."""
    body = await request.body()
    signature = request.headers.get("X-Razorpay-Signature", "")

    if not razorpay_service.verify_webhook_signature(body, signature):
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    event = razorpay_service.parse_webhook_event(body)
    event_type = event.get("event")

    if event_type == "payment.captured":
        plan = razorpay_service.get_plan_from_subscription(event)
        user_id = razorpay_service.get_user_from_subscription(event)

        if plan and user_id:
            try:
                from ..models.db.user import User
                from sqlalchemy import select

                stmt = select(User).where(User.clerk_id == user_id)
                result = await db.execute(stmt)
                db_user = result.scalar_one_or_none()

                if db_user:
                    db_user.plan = plan
                    await db.commit()
                    logger.info("Plan updated to %s for user %s via webhook", plan, user_id)
            except Exception as e:
                logger.error("Webhook plan upgrade failed: %s", e)

    return {"status": "received"}
