from __future__ import annotations

from abc import ABC, abstractmethod

from owo._prompt import SYSTEM_PROMPT, build_user_message


class BaseProvider(ABC):
    """LLM or other completion backend used by :func:`owo.parse`."""

    @abstractmethod
    def complete(self, prompt: str) -> str:
        """Return model output for a single combined prompt string."""

    def complete_messages(self, user_text: str) -> str:
        """Return model output using system + user message split.

        Providers that support a native system role should override this.
        The default falls back to :meth:`complete` with both parts joined.
        """
        return self.complete(SYSTEM_PROMPT + "\n" + build_user_message(user_text))


class BaseSTTProvider(ABC):
    """Speech-to-text backend used by :func:`owo.parse_audio`."""

    @abstractmethod
    def transcribe(self, audio: bytes, *, filename: str = "audio.mp3") -> str:
        """Return a plain-text transcript of *audio*."""
