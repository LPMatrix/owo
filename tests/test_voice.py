from __future__ import annotations

import json
import sys
from types import ModuleType, SimpleNamespace
from unittest.mock import MagicMock

import pytest

from owo import BaseSTTProvider, parse_audio
from owo.providers import BaseProvider

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

FAKE_AUDIO = b"\xff\xfb\x00" * 16  # placeholder bytes


def _make_json(**kwargs) -> str:
    base = {
        "intent": "buy_data",
        "amount": None,
        "currency": "NGN",
        "recipient": None,
        "account_number": "08012345678",
        "bank": None,
        "service": "MTN",
        "language_detected": "en",
        "confidence": 0.92,
        "flags": [],
    }
    base.update(kwargs)
    return json.dumps(base)


def _make_whisper_sdk(transcript: str) -> tuple[ModuleType, MagicMock]:
    mock_client = MagicMock()
    mock_client.audio.transcriptions.create.return_value = SimpleNamespace(text=transcript)
    fake_sdk = ModuleType("openai")
    fake_sdk.OpenAI = MagicMock(return_value=mock_client)
    return fake_sdk, mock_client


# ---------------------------------------------------------------------------
# BaseSTTProvider is abstract
# ---------------------------------------------------------------------------

def test_base_stt_provider_is_abstract() -> None:
    with pytest.raises(TypeError):
        BaseSTTProvider()  # type: ignore[abstract]


# ---------------------------------------------------------------------------
# parse_audio — heuristic-handled transcript (no LLM needed)
# ---------------------------------------------------------------------------

class _FixedSTT(BaseSTTProvider):
    def __init__(self, transcript: str) -> None:
        self._transcript = transcript

    def transcribe(self, audio: bytes, *, filename: str = "audio.mp3") -> str:
        assert audio == FAKE_AUDIO
        return self._transcript


def test_parse_audio_heuristic_transfer() -> None:
    r = parse_audio(FAKE_AUDIO, stt_provider=_FixedSTT("Send 10k to Ada"))
    assert r.intent == "transfer"
    assert r.amount == 10_000.0
    assert r.recipient == "Ada"


def test_parse_audio_heuristic_pidgin() -> None:
    r = parse_audio(FAKE_AUDIO, stt_provider=_FixedSTT("Abeg send 5k to Chidi"))
    assert r.intent == "transfer"
    assert r.language_detected == "pcm"


def test_parse_audio_heuristic_balance() -> None:
    r = parse_audio(FAKE_AUDIO, stt_provider=_FixedSTT("How much I get?"))
    assert r.intent == "balance_check"


def test_parse_audio_filename_forwarded() -> None:
    received: list[str] = []

    class _SpySTT(BaseSTTProvider):
        def transcribe(self, audio: bytes, *, filename: str = "audio.mp3") -> str:
            received.append(filename)
            return "Send 1k to Ada"

    parse_audio(FAKE_AUDIO, stt_provider=_SpySTT(), filename="clip.ogg")
    assert received == ["clip.ogg"]


# ---------------------------------------------------------------------------
# parse_audio — LLM provider called for unknown intents
# ---------------------------------------------------------------------------

class _SpyLLM(BaseProvider):
    called = False

    def complete(self, prompt: str) -> str:
        _SpyLLM.called = True
        return _make_json(intent="buy_data")

    def complete_messages(self, user_text: str) -> str:
        _SpyLLM.called = True
        return _make_json(intent="buy_data")


def test_parse_audio_calls_llm_for_unknown_transcript() -> None:
    _SpyLLM.called = False
    r = parse_audio(
        FAKE_AUDIO,
        stt_provider=_FixedSTT("Buy 2GB data for 08012345678 on MTN"),
        provider=_SpyLLM(),
    )
    assert _SpyLLM.called
    assert r.intent == "buy_data"


def test_parse_audio_no_llm_for_heuristic_transcript() -> None:
    _SpyLLM.called = False
    parse_audio(FAKE_AUDIO, stt_provider=_FixedSTT("Send 10k to Ada"), provider=_SpyLLM())
    assert not _SpyLLM.called


# ---------------------------------------------------------------------------
# WhisperProvider — mocked SDK
# ---------------------------------------------------------------------------

def test_whisper_provider_transcribes_audio() -> None:
    fake_sdk, mock_client = _make_whisper_sdk("Send 20k to Mama")
    with __import__("unittest.mock", fromlist=["patch"]).patch.dict(
        sys.modules, {"openai": fake_sdk}
    ):
        sys.modules.pop("owo.providers.whisper", None)
        from owo.providers.whisper import WhisperProvider

        r = parse_audio(FAKE_AUDIO, stt_provider=WhisperProvider(api_key="k"))

    assert r.intent == "transfer"
    assert r.amount == 20_000.0
    call_kwargs = mock_client.audio.transcriptions.create.call_args.kwargs
    assert call_kwargs["model"] == "whisper-1"


def test_whisper_provider_language_hint_mapped() -> None:
    fake_sdk, mock_client = _make_whisper_sdk("Ran 20k si Mama")
    with __import__("unittest.mock", fromlist=["patch"]).patch.dict(
        sys.modules, {"openai": fake_sdk}
    ):
        sys.modules.pop("owo.providers.whisper", None)
        from owo.providers.whisper import WhisperProvider

        parse_audio(FAKE_AUDIO, stt_provider=WhisperProvider(api_key="k", language="yo"))

    assert mock_client.audio.transcriptions.create.call_args.kwargs["language"] == "yo"


def test_whisper_provider_no_language_hint_for_pidgin() -> None:
    # Pidgin has no Whisper language code — should be passed as None (auto-detect)
    fake_sdk, mock_client = _make_whisper_sdk("Abeg send 5k to Chidi")
    with __import__("unittest.mock", fromlist=["patch"]).patch.dict(
        sys.modules, {"openai": fake_sdk}
    ):
        sys.modules.pop("owo.providers.whisper", None)
        from owo.providers.whisper import WhisperProvider

        parse_audio(FAKE_AUDIO, stt_provider=WhisperProvider(api_key="k", language="pcm"))

    assert mock_client.audio.transcriptions.create.call_args.kwargs["language"] is None


def test_whisper_provider_filename_set_on_file_object() -> None:
    fake_sdk, mock_client = _make_whisper_sdk("Send 5k to Ada")
    with __import__("unittest.mock", fromlist=["patch"]).patch.dict(
        sys.modules, {"openai": fake_sdk}
    ):
        sys.modules.pop("owo.providers.whisper", None)
        from owo.providers.whisper import WhisperProvider

        parse_audio(FAKE_AUDIO, stt_provider=WhisperProvider(api_key="k"), filename="note.ogg")

    file_arg = mock_client.audio.transcriptions.create.call_args.kwargs["file"]
    assert file_arg.name == "note.ogg"
