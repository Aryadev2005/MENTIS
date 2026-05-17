"""Razorpay payment service — order creation, signature verification, webhook handling."""

import hashlib
import hmac
import json
import logging
from typing import Any

import httpx

from ..config import settings  # noqa: F401 — re-exported for router use

logger = logging.getLogger(__name__)

RAZORPAY_API = "https://api.razorpay.com/v1"

PLAN_PRICES = {
    "student": {"amount": 49900, "currency": "INR", "period": "monthly"},  # ₹499/month
    "pro": {"amount": 99900, "currency": "INR", "period": "monthly"},       # ₹999/month
    "oa_pass": {"amount": 19900, "currency": "INR", "period": "one_time"},  # ₹199 one-time
}


def _auth() -> tuple[str, str]:
    return (settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)


async def create_order(plan: str, user_id: str, receipt: str | None = None) -> dict[str, Any]:
    plan_info = PLAN_PRICES.get(plan)
    if not plan_info:
        raise ValueError(f"Unknown plan: {plan}")

    payload = {
        "amount": plan_info["amount"],
        "currency": plan_info["currency"],
        "receipt": receipt or f"mentis_{user_id}_{plan}",
        "notes": {
            "plan": plan,
            "user_id": user_id,
            "product": "MENTIS",
        },
    }

    async with httpx.AsyncClient(auth=_auth(), timeout=10.0) as client:
        response = await client.post(f"{RAZORPAY_API}/orders", json=payload)
        response.raise_for_status()
        return response.json()


def verify_payment_signature(
    order_id: str,
    payment_id: str,
    signature: str,
) -> bool:
    """Verify Razorpay payment signature."""
    message = f"{order_id}|{payment_id}"
    expected = hmac.new(
        settings.RAZORPAY_KEY_SECRET.encode(),
        message.encode(),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


def verify_webhook_signature(body: bytes, signature: str) -> bool:
    """Verify Razorpay webhook signature."""
    expected = hmac.new(
        settings.RAZORPAY_WEBHOOK_SECRET.encode(),
        body,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


async def get_payment_details(payment_id: str) -> dict[str, Any]:
    async with httpx.AsyncClient(auth=_auth(), timeout=10.0) as client:
        response = await client.get(f"{RAZORPAY_API}/payments/{payment_id}")
        response.raise_for_status()
        return response.json()


def parse_webhook_event(body: bytes) -> dict[str, Any]:
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        logger.error("Failed to parse webhook body")
        return {}


def get_plan_from_subscription(event_data: dict) -> str | None:
    notes = event_data.get("payload", {}).get("payment", {}).get("entity", {}).get("notes", {})
    return notes.get("plan")


def get_user_from_subscription(event_data: dict) -> str | None:
    notes = event_data.get("payload", {}).get("payment", {}).get("entity", {}).get("notes", {})
    return notes.get("user_id")
