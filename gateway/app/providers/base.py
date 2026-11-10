from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.core.schemas import ChatMessage, Usage


@dataclass
class ProviderResult:
    content: str
    model: str
    usage: Usage
    finish_reason: str = "stop"


class BaseProvider(ABC):
    name: str

    @abstractmethod
    async def chat(
        self,
        *,
        runtime_id: str,
        messages: list[ChatMessage],
        temperature: float,
        max_tokens: int,
    ) -> ProviderResult:
        raise NotImplementedError

    async def health(self) -> bool:
        return True