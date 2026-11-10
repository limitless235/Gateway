from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import get_gateway_config
from app.core.schemas import ChatMessage
from app.router.complexity import resolve_complexity, score_complexity
from app.router.intent import detect_intent
from app.router.pipeline import route_request


def test_trivial_routes_to_tiny_gpt2():
    cfg = get_gateway_config()
    result = resolve_complexity("hi", cfg.routing, cfg.tiers)
    assert result.tier == "tiny"
    assert result.model == "gpt2-xl"


def test_hard_prompt_routes_toward_large():
    cfg = get_gateway_config()
    text = (
        "Compare the trade-offs of microservices vs monoliths, then architect a production-ready "
        "design and walk me through edge cases step by step."
    )
    result = resolve_complexity(text, cfg.routing, cfg.tiers)
    assert result.score >= 0.45
    assert result.tier in {"medium", "large"}


def test_intent_code_pins_phi3():
    cfg = get_gateway_config()
    match = detect_intent("Write a python function to reverse a linked list", cfg.routing)
    assert match is not None
    assert match.intent == "code"
    assert match.model == "phi3:mini"


def test_intent_story_pins_qwen3b():
    cfg = get_gateway_config()
    match = detect_intent("Write a short story about a lighthouse keeper", cfg.routing)
    assert match is not None
    assert match.intent == "story"
    assert match.model == "qwen2.5:3b"


def test_intent_slogan_pins_gpt2():
    cfg = get_gateway_config()
    match = detect_intent("Give me a catchy slogan for a coffee shop", cfg.routing)
    assert match is not None
    assert match.intent == "slogan"
    assert match.model == "gpt2-xl"


def test_pipeline_intent_beats_complexity():
    cfg = get_gateway_config()
    messages = [ChatMessage(role="user", content="Write python code to sort a list")]
    spec, trace = route_request(messages=messages, cfg=cfg, auto_route=True)
    assert spec.name == "phi3:mini"
    assert trace.intent == "code"
    assert "intent:code" in trace.reason


def test_force_model_bypasses_router():
    cfg = get_gateway_config()
    messages = [ChatMessage(role="user", content="Write python code to sort a list")]
    spec, trace = route_request(
        messages=messages,
        cfg=cfg,
        auto_route=False,
        force_model="qwen2.5:0.5b",
    )
    assert spec.name == "qwen2.5:0.5b"
    assert trace.forced is True


def test_score_monotonic_with_length():
    cfg = get_gateway_config()
    short = score_complexity("ok", cfg.routing)
    long = score_complexity("word " * 200, cfg.routing)
    assert long > short