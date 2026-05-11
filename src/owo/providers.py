from __future__ import annotations

from abc import ABC, abstractmethod


class BaseProvider(ABC):
    """LLM or other completion backend used by :func:`owo.parse`."""

    @abstractmethod
    def complete(self, prompt: str) -> str:
        """Return model output (typically JSON) for the given prompt."""
