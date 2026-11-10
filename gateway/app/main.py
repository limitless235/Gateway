from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import chat as chat_routes
from app.core.config import get_gateway_config
from app.core.schemas import HealthResponse
from app.providers.registry import get_provider_registry
from app.services.chat import ChatService

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("gateway")


@asynccontextmanager
async def lifespan(app: FastAPI):
    cfg = get_gateway_config()
    providers = get_provider_registry()
    app.state.cfg = cfg
    app.state.providers = providers
    app.state.chat_service = ChatService(cfg, providers)
    logger.info("Gateway ready with models: %s", ", ".join(cfg.models.keys()))
    yield


app = FastAPI(
    title="Local AI Gateway",
    description="LiteLLM-inspired local gateway with capability + intent routing and guardrails.",
    version="0.1.0",
    lifespan=lifespan,
)

cfg = get_gateway_config()
app.add_middleware(
    CORSMiddleware,
    allow_origins=cfg.settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_routes.router, prefix="/v1")


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    cfg = app.state.cfg
    providers = app.state.providers
    ollama_ok = await providers.ollama.health()
    return HealthResponse(
        status="ok",
        models=[
            {
                "id": m.name,
                "tier": m.tier,
                "capability": m.capability,
                "provider": m.provider,
            }
            for m in sorted(cfg.models.values(), key=lambda x: x.capability)
        ],
        ollama_ok=ollama_ok,
        gpt2_enabled=cfg.settings.enable_gpt2,
    )


@app.get("/")
async def root():
    return {
        "name": "Local AI Gateway",
        "docs": "/docs",
        "chat": "POST /v1/chat/completions",
        "health": "/health",
    }