from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

CONFIG_DIR = Path(__file__).resolve().parents[2] / "config"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="GATEWAY_")

    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173", "http://127.0.0.1:5173"])
    models_config_path: Path = CONFIG_DIR / "models.yaml"
    routing_config_path: Path = CONFIG_DIR / "routing.yaml"
    gpt2_device: str = "mps"  # Apple Silicon; falls back to cpu in provider
    enable_gpt2: bool = True


class ModelSpec(BaseModel):
    name: str
    provider: str
    runtime_id: str
    tier: str
    capability: int
    description: str = ""


class GatewayConfig(BaseModel):
    settings: Settings
    models: dict[str, ModelSpec]
    tiers: dict[str, str]
    fallback_model: str
    ollama_base_url: str
    request_timeout_s: float
    routing: dict[str, Any]


def _load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


@lru_cache
def get_settings() -> Settings:
    return Settings()


@lru_cache
def get_gateway_config() -> GatewayConfig:
    settings = get_settings()
    models_raw = _load_yaml(settings.models_config_path)
    routing_raw = _load_yaml(settings.routing_config_path)

    defaults = models_raw.get("defaults", {})
    models: dict[str, ModelSpec] = {}
    for name, spec in (models_raw.get("models") or {}).items():
        models[name] = ModelSpec(name=name, **spec)

    return GatewayConfig(
        settings=settings,
        models=models,
        tiers=models_raw.get("tiers") or {},
        fallback_model=defaults.get("fallback_model", "qwen2.5:0.5b"),
        ollama_base_url=defaults.get("ollama_base_url", "http://localhost:11434/v1"),
        request_timeout_s=float(defaults.get("request_timeout_s", 120)),
        routing=routing_raw,
    )