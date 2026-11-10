from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


@dataclass
class IntentMatch:
    intent: str
    model: str
    reason: str


def detect_intent(text: str, routing_cfg: dict[str, Any]) -> IntentMatch | None:
    intents = routing_cfg.get("intents") or {}
    for name, spec in intents.items():
        patterns = spec.get("patterns") or []
        for pattern in patterns:
            if re.search(pattern, text):
                model = spec["model"]
                return IntentMatch(
                    intent=name,
                    model=model,
                    reason=f"intent:{name} → {model}",
                )
    return None