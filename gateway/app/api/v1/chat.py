from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from app.core.schemas import ChatCompletionRequest, ChatCompletionResponse, ModelsListResponse

router = APIRouter()


def _service(request: Request):
    return request.app.state.chat_service


@router.post("/chat/completions", response_model=ChatCompletionResponse)
async def chat_completions(body: ChatCompletionRequest, request: Request) -> ChatCompletionResponse:
    if body.stream:
        raise HTTPException(status_code=400, detail="Streaming is not supported in this demo gateway yet.")
    if not body.messages:
        raise HTTPException(status_code=400, detail="messages must not be empty")
    try:
        return await _service(request).complete(body)
    except KeyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/models", response_model=ModelsListResponse)
async def list_models(request: Request) -> ModelsListResponse:
    return ModelsListResponse(data=_service(request).list_models())