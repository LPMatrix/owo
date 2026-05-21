from __future__ import annotations

import io
import os

try:
    from openai import OpenAI as _OpenAI
except ImportError as exc:
    raise ImportError(
        "Install the OpenAI SDK: pip install 'owo-parse[voice]'"
    ) from exc

from owo.providers import BaseSTTProvider

_DEFAULT_MODEL = "whisper-1"

# Whisper language codes for supported Nigerian languages.
# Pidgin (pcm) has no ISO 639-1 code Whisper recognises — omit for auto-detect.
WHISPER_LANGUAGE_MAP: dict[str, str] = {
    "en": "en",
    "yo": "yo",
    "ha": "ha",
    "ig": "ig",
}


class WhisperProvider(BaseSTTProvider):
    """STT provider backed by OpenAI Whisper.

    - ``OWO_WHISPER_MODEL`` — default: ``whisper-1``
    - ``OPENAI_API_KEY``    — required (read by the SDK automatically)

    Pass ``language`` to bias transcription toward a specific Nigerian language.
    Accepted values: ``"en"``, ``"yo"``, ``"ha"``, ``"ig"``.
    Omit (or pass ``None``) for automatic detection, which works best for
    Nigerian Pidgin and code-switched speech.

    Usage::

        from owo import parse_audio
        from owo.providers.whisper import WhisperProvider

        with open("voice_note.ogg", "rb") as f:
            result = parse_audio(f.read(), stt_provider=WhisperProvider())
    """

    def __init__(
        self,
        model: str | None = None,
        *,
        api_key: str | None = None,
        language: str | None = None,
    ) -> None:
        self._client = _OpenAI(api_key=api_key)
        self._model = model or os.environ.get("OWO_WHISPER_MODEL", _DEFAULT_MODEL)
        self._language = WHISPER_LANGUAGE_MAP.get(language or "", None) if language else None

    def transcribe(self, audio: bytes, *, filename: str = "audio.mp3") -> str:
        audio_file = io.BytesIO(audio)
        audio_file.name = filename
        response = self._client.audio.transcriptions.create(
            model=self._model,
            file=audio_file,
            language=self._language,
        )
        return response.text
