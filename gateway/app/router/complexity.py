from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


@dataclass
class ComplexityResult:
    score: float
    tier: str
    model: str
    reason: str


def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, value))


def score_complexity(text: str, routing_cfg: dict[str, Any]) -> float:
    cfg = routing_cfg.get("complexity") or {}
    weights = cfg.get("weights") or {}
    w_len = float(weights.get("length", 0.35))
    w_multi = float(weights.get("multi_step", 0.35))
    w_diff = float(weights.get("difficulty_keywords", 0.30))

    # Length: ~0 at <20 chars, ~1 at 800+ chars
    length_score = _clamp(len(text.strip()) / 800.0)

    multi_hits = sum(1 for p in (cfg.get("multi_step_patterns") or []) if re.search(p, text, re.M))
    multi_score = _clamp(multi_hits / 2.0)

    diff_hits = sum(1 for p in (cfg.get("difficulty_patterns") or []) if re.search(p, text, re.M))
    diff_score = _clamp(diff_hits / 2.0)

    trivial = any(re.search(p, text, re.M) for p in (cfg.get("trivial_patterns") or []))
    if trivial and len(text.strip()) < 80:
        return 0.05

    return _clamp(w_len * length_score + w_multi * multi_score + w_diff * diff_score)


def tier_for_score(score: float, routing_cfg: dict[str, Any], tiers: dict[str, str]) -> tuple[str, str]:
    thresholds = (routing_cfg.get("complexity") or {}).get("thresholds") or {}
    ordered = [
        ("tiny", float(thresholds.get("tiny", 0.20))),
        ("small", float(thresholds.get("small", 0.45))),
        ("medium", float(thresholds.get("medium", 0.70))),
        ("large", float(thresholds.get("large", 1.01))),
    ]
    for tier_name, upper in ordered:
        if score < upper:
            model = tiers[tier_name]
            return tier_name, model
    model = tiers.get("large") or next(iter(tiers.values()))
    return "large", model


def resolve_complexity(
    text: str,
    routing_cfg: dict[str, Any],
    tiers: dict[str, str],
) -> ComplexityResult:
    score = score_complexity(text, routing_cfg)
    tier, model = tier_for_score(score, routing_cfg, tiers)
    return ComplexityResult(
        score=round(score, 3),
        tier=tier,
        model=model,
        reason=f"complexity:{score:.2f} → tier:{tier} → {model}",
    )