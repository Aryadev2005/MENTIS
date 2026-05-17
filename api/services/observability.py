"""LangSmith tracing + Prometheus metrics for MENTIS API."""

import functools
import logging
import time
from typing import Any, Callable

logger = logging.getLogger(__name__)

try:
    from langsmith import Client as LangSmithClient
    from langsmith import traceable
    _LANGSMITH_AVAILABLE = True
except ImportError:
    _LANGSMITH_AVAILABLE = False
    logger.warning("LangSmith not installed — tracing disabled")

try:
    from prometheus_client import Counter, Histogram, Gauge

    llm_requests_total = Counter(
        "mentis_llm_requests_total",
        "Total LLM API calls",
        ["model", "operation", "status"],
    )
    llm_latency_seconds = Histogram(
        "mentis_llm_latency_seconds",
        "LLM call latency",
        ["model", "operation"],
        buckets=[0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0],
    )
    active_sessions = Gauge(
        "mentis_active_sessions",
        "Currently active interview sessions",
    )
    oa_solves_total = Counter(
        "mentis_oa_solves_total",
        "Total OA questions solved",
        ["question_type", "department"],
    )
    answer_confidence = Histogram(
        "mentis_answer_confidence",
        "Distribution of answer confidence scores",
        ["question_type"],
        buckets=[10, 20, 30, 40, 50, 60, 70, 80, 90, 100],
    )
    _PROMETHEUS_AVAILABLE = True
except ImportError:
    _PROMETHEUS_AVAILABLE = False
    logger.warning("prometheus_client not installed — metrics disabled")


def trace_llm(operation: str, model: str = "claude"):
    """Decorator: wraps async functions with LangSmith tracing + Prometheus metrics."""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            start = time.perf_counter()
            status = "success"
            result = None

            try:
                if _LANGSMITH_AVAILABLE:
                    traced_func = traceable(
                        name=f"mentis.{operation}",
                        tags=["mentis", operation, model],
                    )(func)
                    result = await traced_func(*args, **kwargs)
                else:
                    result = await func(*args, **kwargs)
                return result

            except Exception as e:
                status = "error"
                logger.error("LLM call failed [%s/%s]: %s", model, operation, e)
                raise

            finally:
                elapsed = time.perf_counter() - start
                if _PROMETHEUS_AVAILABLE:
                    llm_requests_total.labels(
                        model=model, operation=operation, status=status
                    ).inc()
                    llm_latency_seconds.labels(
                        model=model, operation=operation
                    ).observe(elapsed)

        return wrapper
    return decorator


def record_oa_solve(question_type: str, department: str, confidence: float):
    if _PROMETHEUS_AVAILABLE:
        oa_solves_total.labels(
            question_type=question_type,
            department=department,
        ).inc()
        answer_confidence.labels(question_type=question_type).observe(confidence)


def increment_sessions(delta: int = 1):
    if _PROMETHEUS_AVAILABLE:
        active_sessions.inc(delta)


def decrement_sessions(delta: int = 1):
    if _PROMETHEUS_AVAILABLE:
        active_sessions.dec(delta)


def setup_langsmith(api_key: str | None = None):
    """Initialize LangSmith client."""
    if not _LANGSMITH_AVAILABLE:
        return None
    try:
        import os
        if api_key:
            os.environ["LANGCHAIN_API_KEY"] = api_key
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGCHAIN_PROJECT"] = "mentis-prod"
        client = LangSmithClient()
        logger.info("LangSmith tracing initialized")
        return client
    except Exception as e:
        logger.warning("LangSmith init failed: %s", e)
        return None
