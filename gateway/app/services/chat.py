from __future__ import annotations

import logging
import time
from typing import Any

import httpx

from app.core.config import GatewayConfig
from app.core.schemas import (
    ChatChoice,
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatMessage,
    GuardrailEvent,
    Usage,
)
from app.guardrails.post_call import run_post_call_guardrails
from app.guardrails.pre_call import run_pre_call_guardrails
from app.observability.trace import build_trace, new_request_id, timed
from app.providers.registry import ProviderRegistry
from app.router.pipeline import route_request

logger = logging.getLogger(__name__)


class ChatService:
    def __init__(self, cfg: GatewayConfig, providers: ProviderRegistry) -> None:
        self.cfg = cfg
        self.providers = providers

    async def complete(self, body: ChatCompletionRequest) -> ChatCompletionResponse:
        request_id = new_request_id()
        created = int(time.time())
        guardrail_events: list[GuardrailEvent] = []

        with timed() as latency_box:
            pre = run_pre_call_guardrails(body.messages)
            guardrail_events.extend(pre.events)

            if pre.blocked:
                # Still compute routing for the trace so the UI shows what *would* have happened
                try:
                    spec, routing = route_request(
                        messages=pre.messages,
                        cfg=self.cfg,
                        auto_route=body.auto_route,
                        force_model=body.force_model,
                        requested_model=body.model,
                    )
                except Exception:
                    fallback = self.cfg.models[self.cfg.fallback_model]
                    from app.core.schemas import RoutingTrace

                    spec = fallback
                    routing = RoutingTrace(
                        chosen_model=fallback.name,
                        provider=fallback.provider,
                        reason="blocked_before_route",
                        tier=fallback.tier,
                    )

                trace = build_trace(
                    request_id=request_id,
                    routing=routing,
                    guardrails=guardrail_events,
                    latency_ms=0.0,
                    blocked=True,
                )
                return ChatCompletionResponse(
                    id=request_id,
                    created=created,
                    model=spec.name,
                    choices=[
                        ChatChoice(
                            message=ChatMessage(role="assistant", content=pre.block_message),
                            finish_reason="content_filter",
                        )
                    ],
                    usage=Usage(),
                    gateway_trace=trace,
                )

            spec, routing = route_request(
                messages=pre.messages,
                cfg=self.cfg,
                auto_route=body.auto_route,
                force_model=body.force_model,
                requested_model=body.model,
            )

            content, usage, finish_reason = await self._call_with_fallback(
                spec_name=spec.name,
                messages=pre.messages,
                temperature=body.temperature or 0.7,
                max_tokens=body.max_tokens or 256,
            )

            post = run_post_call_guardrails(content)
            guardrail_events.extend(post.events)
            content = post.content

        trace = build_trace(
            request_id=request_id,
            routing=routing,
            guardrails=guardrail_events,
            latency_ms=round(latency_box[0], 2),
            blocked=post.blocked,
        )

        return ChatCompletionResponse(
            id=request_id,
            created=created,
            model=spec.name,
            choices=[
                ChatChoice(
                    message=ChatMessage(role="assistant", content=content),
                    finish_reason="content_filter" if post.blocked else finish_reason,
                )
            ],
            usage=usage,
            gateway_trace=trace,
        )

    async def _call_with_fallback(
        self,
        *,
        spec_name: str,
        messages: list[ChatMessage],
        temperature: float,
        max_tokens: int,
    ) -> tuple[str, Usage, str]:
        attempted = [spec_name]
        fallback = self.cfg.fallback_model
        if fallback not in attempted:
            attempted.append(fallback)

        last_error: Exception | None = None
        for name in attempted:
            model = self.cfg.models[name]
            provider = self.providers.get(model.provider)
            try:
                result = await provider.chat(
                    runtime_id=model.runtime_id,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                return result.content, result.usage, result.finish_reason
            except (httpx.HTTPError, RuntimeError, OSError) as exc:
                logger.warning("Provider call failed for %s: %s", name, exc)
                last_error = exc
                continue

        raise RuntimeError(f"All providers failed. Last error: {last_error}")

    def list_models(self) -> list[dict[str, Any]]:
        return [
            {
                "id": m.name,
                "object": "model",
                "owned_by": m.provider,
                "tier": m.tier,
                "capability": m.capability,
                "description": m.description,
            }
            for m in sorted(self.cfg.models.values(), key=lambda x: x.capability)
        ]