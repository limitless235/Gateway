from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.core.schemas import ChatMessage, GuardrailEvent
from app.guardrails.pii import redact_pii

INJECTION_PATTERNS = [
    re.compile(r"(?i)\bignore (all |any )?(previous|prior|above) (instructions|prompts)\b"),
    re.compile(r"(?i)\bdan mode\b"),
    re.compile(r"(?i)\bjailbreak\b"),
    re.compile(r"(?i)\boverride (your|the) system prompt\b"),
]

BLOCKED_TOPICS = [
    re.compile(r"(?i)\bhow to make a (bomb|explosive)\b"),
    re.compile(r"(?i)\bchild (sexual|porn)\b"),
]

MAX_INPUT_CHARS = 8000


@dataclass
class PreCallResult:
    messages: list[ChatMessage]
    events: list[GuardrailEvent] = field(default_factory=list)
    blocked: bool = False
    block_message: str = ""


def run_pre_call_guardrails(messages: list[ChatMessage]) -> PreCallResult:
    events: list[GuardrailEvent] = []
    updated: list[ChatMessage] = []

    for msg in messages:
        text = msg.content

        if len(text) > MAX_INPUT_CHARS:
            events.append(
                GuardrailEvent(
                    stage="pre_call",
                    name="max_input_length",
                    action="block",
                    detail=f"input exceeded {MAX_INPUT_CHARS} chars",
                )
            )
            return PreCallResult(
                messages=messages,
                events=events,
                blocked=True,
                block_message="Request blocked: input too long.",
            )

        for pattern in BLOCKED_TOPICS:
            if pattern.search(text):
                events.append(
                    GuardrailEvent(
                        stage="pre_call",
                        name="blocked_topic",
                        action="block",
                        detail=pattern.pattern,
                    )
                )
                return PreCallResult(
                    messages=messages,
                    events=events,
                    blocked=True,
                    block_message="Request blocked by content policy.",
                )

        for pattern in INJECTION_PATTERNS:
            if pattern.search(text):
                events.append(
                    GuardrailEvent(
                        stage="pre_call",
                        name="prompt_injection",
                        action="block",
                        detail=pattern.pattern,
                    )
                )
                return PreCallResult(
                    messages=messages,
                    events=events,
                    blocked=True,
                    block_message="Request blocked: prompt injection detected.",
                )

        pii = redact_pii(text)
        if pii.redacted:
            events.append(
                GuardrailEvent(
                    stage="pre_call",
                    name="pii_redaction",
                    action="redact",
                    detail=",".join(pii.findings),
                )
            )
            updated.append(ChatMessage(role=msg.role, content=pii.text))
        else:
            updated.append(msg)

    if not events:
        events.append(
            GuardrailEvent(stage="pre_call", name="pre_call_pass", action="allow", detail="ok")
        )

    return PreCallResult(messages=updated, events=events, blocked=False)