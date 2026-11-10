from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.core.schemas import GuardrailEvent
from app.guardrails.pii import redact_pii

FORBIDDEN_OUTPUT = [
    re.compile(r"(?i)\bapi[_-]?key\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{16,}"),
    re.compile(r"(?i)\bsk-[A-Za-z0-9]{20,}"),
]


@dataclass
class PostCallResult:
    content: str
    events: list[GuardrailEvent] = field(default_factory=list)
    blocked: bool = False


def run_post_call_guardrails(content: str) -> PostCallResult:
    events: list[GuardrailEvent] = []
    text = content

    for pattern in FORBIDDEN_OUTPUT:
        if pattern.search(text):
            events.append(
                GuardrailEvent(
                    stage="post_call",
                    name="secret_leak",
                    action="block",
                    detail=pattern.pattern,
                )
            )
            return PostCallResult(
                content="Response blocked: potential secret leakage in model output.",
                events=events,
                blocked=True,
            )

    pii = redact_pii(text)
    if pii.redacted:
        events.append(
            GuardrailEvent(
                stage="post_call",
                name="pii_redaction",
                action="redact",
                detail=",".join(pii.findings),
            )
        )
        text = pii.text
    else:
        events.append(
            GuardrailEvent(stage="post_call", name="post_call_pass", action="allow", detail="ok")
        )

    return PostCallResult(content=text, events=events, blocked=False)