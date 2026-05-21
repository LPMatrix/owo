from __future__ import annotations

from importlib.metadata import version as _version

from owo._heuristic import heuristic_parse as _heuristic_parse
from owo._heuristic import result_from_provider_json as _result_from_provider_json
from owo.providers import BaseProvider, BaseSTTProvider
from owo.schema import Intent, Language, OwoResult


def parse(text: str, *, provider: BaseProvider | None = None) -> OwoResult:
    """
    Parse a free-form financial instruction into structured fields.

    The heuristic runs first in all cases. When a *provider* is supplied,
    it is called only for inputs the heuristic cannot confidently handle
    (i.e. the result carries a ``needs_llm_provider`` flag).
    """
    result = _heuristic_parse(text)
    if provider is None or "needs_llm_provider" not in result.flags:
        return result
    out = provider.complete_messages(text)
    return _result_from_provider_json(out, text)


def parse_audio(
    audio: bytes,
    *,
    stt_provider: BaseSTTProvider,
    provider: BaseProvider | None = None,
    filename: str = "audio.mp3",
) -> OwoResult:
    """
    Transcribe *audio* then parse the transcript into structured fields.

    *audio* should be raw audio bytes in any format Whisper accepts
    (mp3, mp4, ogg, wav, webm, …). Pass *filename* to hint the format when
    the extension matters for your STT backend.

    *stt_provider* handles transcription; the optional *provider* is forwarded
    to :func:`parse` for LLM fallback on complex intents.
    """
    transcript = stt_provider.transcribe(audio, filename=filename)
    return parse(transcript, provider=provider)


__version__: str = _version("owo-parse")

__all__ = [
    "__version__",
    "BaseProvider",
    "BaseSTTProvider",
    "Intent",
    "Language",
    "OwoResult",
    "parse",
    "parse_audio",
]
