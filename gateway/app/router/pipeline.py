from __future__ import annotations

from app.core.config import GatewayConfig, ModelSpec
from app.core.schemas import ChatMessage, RoutingTrace
from app.router.complexity import resolve_complexity
from app.router.intent import detect_intent


def _latest_user_text(messages: list[ChatMessage]) -> str:
    for msg in reversed(messages):
        if msg.role == "user":
            return msg.content
    return " ".join(m.content for m in messages)


def route_request(
    *,
    messages: list[ChatMessage],
    cfg: GatewayConfig,
    auto_route: bool = True,
    force_model: str | None = None,
    requested_model: str | None = None,
) -> tuple[ModelSpec, RoutingTrace]:
    """Return chosen model spec + routing trace.

    Priority:
    1. force_model / explicit model when auto_route is False
    2. intent specialty map (if intent_priority)
    3. capability / complexity tier
    """
    text = _latest_user_text(messages)

    if force_model or (requested_model and not auto_route):
        name = force_model or requested_model or cfg.fallback_model
        if name not in cfg.models:
            raise KeyError(f"Unknown model: {name}")
        spec = cfg.models[name]
        trace = RoutingTrace(
            intent=None,
            complexity_score=None,
            tier=spec.tier,
            chosen_model=spec.name,
            provider=spec.provider,
            reason=f"forced → {spec.name}",
            forced=True,
        )
        return spec, trace

    # If client passes a concrete model name while auto_route stays true,
    # still allow auto unless they set auto_route=false.
    routing_cfg = cfg.routing
    intent_priority = bool(routing_cfg.get("intent_priority", True))

    if intent_priority:
        match = detect_intent(text, routing_cfg)
        if match:
            if match.model not in cfg.models:
                raise KeyError(f"Intent model missing from registry: {match.model}")
            spec = cfg.models[match.model]
            trace = RoutingTrace(
                intent=match.intent,
                complexity_score=None,
                tier=spec.tier,
                chosen_model=spec.name,
                provider=spec.provider,
                reason=match.reason,
                forced=False,
            )
            return spec, trace

    result = resolve_complexity(text, routing_cfg, cfg.tiers)
    if result.model not in cfg.models:
        raise KeyError(f"Tier model missing from registry: {result.model}")
    spec = cfg.models[result.model]
    trace = RoutingTrace(
        intent=None,
        complexity_score=result.score,
        tier=result.tier,
        chosen_model=spec.name,
        provider=spec.provider,
        reason=result.reason,
        forced=False,
    )
    return spec, trace