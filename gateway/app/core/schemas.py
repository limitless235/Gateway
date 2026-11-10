from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str


class ChatCompletionRequest(BaseModel):
    model: str | None = None
    messages: list[ChatMessage]
    temperature: float | None = 0.7
    max_tokens: int | None = 256
    stream: bool = False
    # Gateway extensions
    auto_route: bool = True
    force_model: str | None = None


class ChatChoice(BaseModel):
    index: int = 0
    message: ChatMessage
    finish_reason: str = "stop"


class Usage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class GuardrailEvent(BaseModel):
    stage: Literal["pre_call", "post_call"]
    name: str
    action: Literal["allow", "redact", "block"]
    detail: str = ""


class RoutingTrace(BaseModel):
    intent: str | None = None
    complexity_score: float | None = None
    tier: str | None = None
    chosen_model: str
    provider: str
    reason: str
    forced: bool = False


class RequestTrace(BaseModel):
    request_id: str
    routing: RoutingTrace
    guardrails: list[GuardrailEvent] = Field(default_factory=list)
    latency_ms: float = 0.0
    blocked: bool = False


class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: list[ChatChoice]
    usage: Usage = Field(default_factory=Usage)
    gateway_trace: RequestTrace | None = None


class HealthResponse(BaseModel):
    status: str
    models: list[dict[str, Any]]
    ollama_ok: bool
    gpt2_enabled: bool


class ModelsListResponse(BaseModel):
    object: str = "list"
    data: list[dict[str, Any]]