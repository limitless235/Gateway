from __future__ import annotations

import httpx

from app.core.schemas import ChatMessage, Usage
from app.providers.base import BaseProvider, ProviderResult


class OllamaProvider(BaseProvider):
    name = "ollama"

    def __init__(self, base_url: str, timeout_s: float = 120.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_s = timeout_s

    async def chat(
        self,
        *,
        runtime_id: str,
        messages: list[ChatMessage],
        temperature: float,
        max_tokens: int,
    ) -> ProviderResult:
        payload = {
            "model": runtime_id,
            "messages": [m.model_dump() for m in messages],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }
        async with httpx.AsyncClient(timeout=self.timeout_s) as client:
            resp = await client.post(f"{self.base_url}/chat/completions", json=payload)
            resp.raise_for_status()
            data = resp.json()

        choice = (data.get("choices") or [{}])[0]
        message = choice.get("message") or {}
        usage_raw = data.get("usage") or {}
        usage = Usage(
            prompt_tokens=int(usage_raw.get("prompt_tokens") or 0),
            completion_tokens=int(usage_raw.get("completion_tokens") or 0),
            total_tokens=int(usage_raw.get("total_tokens") or 0),
        )
        return ProviderResult(
            content=str(message.get("content") or ""),
            model=runtime_id,
            usage=usage,
            finish_reason=str(choice.get("finish_reason") or "stop"),
        )

    async def health(self) -> bool:
        try:
            root = self.base_url.replace("/v1", "")
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{root}/api/tags")
                return resp.status_code == 200
        except Exception:
            return False