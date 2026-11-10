from __future__ import annotations

import time
import uuid
from contextlib import contextmanager
from typing import Iterator

from app.core.schemas import GuardrailEvent, RequestTrace, RoutingTrace


def new_request_id() -> str:
    return f"req_{uuid.uuid4().hex[:12]}"


def build_trace(
    *,
    request_id: str,
    routing: RoutingTrace,
    guardrails: list[GuardrailEvent] | None = None,
    latency_ms: float = 0.0,
    blocked: bool = False,
) -> RequestTrace:
    return RequestTrace(
        request_id=request_id,
        routing=routing,
        guardrails=guardrails or [],
        latency_ms=latency_ms,
        blocked=blocked,
    )


@contextmanager
def timed() -> Iterator[list[float]]:
    """Yield a mutable [elapsed_ms] filled on exit."""
    box: list[float] = [0.0]
    start = time.perf_counter()
    try:
        yield box
    finally:
        box[0] = (time.perf_counter() - start) * 1000.0