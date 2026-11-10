from __future__ import annotations

import asyncio
import logging
from functools import lru_cache
from typing import Any

from app.core.schemas import ChatMessage, Usage
from app.providers.base import BaseProvider, ProviderResult

logger = logging.getLogger(__name__)


def _messages_to_prompt(messages: list[ChatMessage]) -> str:
    """Wrap chat turns into a completion-style prompt for GPT-2."""
    parts: list[str] = []
    for m in messages:
        if m.role == "system":
            parts.append(f"Instructions: {m.content.strip()}")
        elif m.role == "user":
            parts.append(f"User: {m.content.strip()}")
        else:
            parts.append(f"Assistant: {m.content.strip()}")
    parts.append("Assistant:")
    return "\n".join(parts)


class GPT2LocalProvider(BaseProvider):
    name = "gpt2_local"

    def __init__(self, device: str = "mps") -> None:
        self.device_pref = device
        self._models: dict[str, Any] = {}
        self._tokenizers: dict[str, Any] = {}
        self._lock = asyncio.Lock()

    def _resolve_device(self) -> str:
        try:
            import torch

            if self.device_pref == "mps" and torch.backends.mps.is_available():
                return "mps"
            if torch.cuda.is_available():
                return "cuda"
        except Exception:
            pass
        return "cpu"

    def _load_sync(self, runtime_id: str) -> tuple[Any, Any, str]:
        from transformers import AutoModelForCausalLM, AutoTokenizer
        import torch

        device = self._resolve_device()
        logger.info("Loading %s on %s", runtime_id, device)
        tokenizer = AutoTokenizer.from_pretrained(runtime_id)
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token
        model = AutoModelForCausalLM.from_pretrained(runtime_id)
        model.to(device)
        model.eval()
        return tokenizer, model, device

    async def _ensure_loaded(self, runtime_id: str) -> tuple[Any, Any, str]:
        async with self._lock:
            if runtime_id in self._models:
                return self._tokenizers[runtime_id], self._models[runtime_id], self._resolve_device()
            tokenizer, model, device = await asyncio.to_thread(self._load_sync, runtime_id)
            self._tokenizers[runtime_id] = tokenizer
            self._models[runtime_id] = model
            return tokenizer, model, device

    def _generate_sync(
        self,
        tokenizer: Any,
        model: Any,
        device: str,
        prompt: str,
        temperature: float,
        max_tokens: int,
    ) -> tuple[str, int, int]:
        import torch

        inputs = tokenizer(prompt, return_tensors="pt")
        inputs = {k: v.to(device) for k, v in inputs.items()}
        prompt_tokens = int(inputs["input_ids"].shape[-1])

        gen_kwargs: dict[str, Any] = {
            "max_new_tokens": max(1, min(max_tokens, 256)),
            "pad_token_id": tokenizer.eos_token_id,
            "eos_token_id": tokenizer.eos_token_id,
        }
        if temperature and temperature > 0:
            gen_kwargs.update(
                {
                    "do_sample": True,
                    "temperature": max(0.1, float(temperature)),
                    "top_p": 0.9,
                }
            )
        else:
            gen_kwargs["do_sample"] = False

        with torch.no_grad():
            output_ids = model.generate(**inputs, **gen_kwargs)

        new_tokens = output_ids[0][prompt_tokens:]
        text = tokenizer.decode(new_tokens, skip_special_tokens=True).strip()
        # Stop at a pseudo turn boundary if the model rambles
        for stop in ("\nUser:", "\nInstructions:"):
            if stop in text:
                text = text.split(stop, 1)[0].strip()
        return text, prompt_tokens, int(new_tokens.shape[-1])

    async def chat(
        self,
        *,
        runtime_id: str,
        messages: list[ChatMessage],
        temperature: float,
        max_tokens: int,
    ) -> ProviderResult:
        tokenizer, model, device = await self._ensure_loaded(runtime_id)
        prompt = _messages_to_prompt(messages)
        content, prompt_tokens, completion_tokens = await asyncio.to_thread(
            self._generate_sync,
            tokenizer,
            model,
            device,
            prompt,
            temperature,
            max_tokens,
        )
        return ProviderResult(
            content=content or "(empty generation)",
            model=runtime_id,
            usage=Usage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
            ),
        )

    async def health(self) -> bool:
        try:
            import transformers  # noqa: F401
            import torch  # noqa: F401

            return True
        except Exception:
            return False


@lru_cache
def get_gpt2_provider(device: str = "mps") -> GPT2LocalProvider:
    return GPT2LocalProvider(device=device)