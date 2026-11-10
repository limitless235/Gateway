from __future__ import annotations

from functools import lru_cache

from app.core.config import GatewayConfig, get_gateway_config
from app.providers.base import BaseProvider
from app.providers.gpt2_local import GPT2LocalProvider
from app.providers.ollama import OllamaProvider


class ProviderRegistry:
    def __init__(self, cfg: GatewayConfig) -> None:
        self.cfg = cfg
        self._ollama = OllamaProvider(cfg.ollama_base_url, cfg.request_timeout_s)
        self._gpt2 = GPT2LocalProvider(device=cfg.settings.gpt2_device)
        self._by_name: dict[str, BaseProvider] = {
            "ollama": self._ollama,
            "gpt2_local": self._gpt2,
        }

    def get(self, provider_name: str) -> BaseProvider:
        if provider_name not in self._by_name:
            raise KeyError(f"Unknown provider: {provider_name}")
        if provider_name == "gpt2_local" and not self.cfg.settings.enable_gpt2:
            raise RuntimeError("GPT-2 provider disabled (GATEWAY_ENABLE_GPT2=false)")
        return self._by_name[provider_name]

    @property
    def ollama(self) -> OllamaProvider:
        return self._ollama

    @property
    def gpt2(self) -> GPT2LocalProvider:
        return self._gpt2


@lru_cache
def get_provider_registry() -> ProviderRegistry:
    return ProviderRegistry(get_gateway_config())