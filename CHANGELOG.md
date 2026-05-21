# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

---

## [0.2.0] — 2026-05-21

### Added

- **Voice input**: `parse_audio(audio, *, stt_provider, provider=None)` — transcribes
  audio bytes via an STT backend then parses the transcript with the existing pipeline.
- `BaseSTTProvider` abstract class (`owo.providers`) — one method:
  `transcribe(audio: bytes, *, filename: str) -> str`. Subclass to bring any STT backend.
- `WhisperProvider` (`owo.providers.whisper`) — backed by OpenAI Whisper;
  supports language hints for `en`, `yo`, `ha`, `ig`; auto-detects for Pidgin.
  Install with `pip install 'owo-parse[voice]'`.
- `owo.__version__` — package version string, readable at runtime via
  `importlib.metadata`.
- Open source scaffolding: license, security policy, code of conduct, CI, and
  issue templates.
- Minimal `owo` package layout with `parse()`, `OwoResult`, and `BaseProvider`.
- `Intent` and `Language` typed enums (`str, Enum`) in `owo.schema`; `result.py`
  re-exports them for backwards compatibility.
- Offline heuristic coverage for all five supported languages: English (`en`),
  Nigerian Pidgin (`pcm`), Yoruba (`yo`), Hausa (`ha`), and Igbo (`ig`).
- Naija numeric notation: `Xk` (thousands), `X milli` / `half a milli`
  (millions).
- Bank name extraction from "RECIPIENT, BANK" patterns — recognises the 20
  most common Nigerian banks.
- Eval runner (`python -m owo.eval`) with per-language / per-intent / field
  accuracy summary; `--provider MODULE:CLASS` flag (also `OWO_PROVIDER` env
  var) to run provider-backed fixtures in CI.
- `requires_provider: true` fixture flag to skip provider-dependent cases in
  offline runs.
- `AnthropicProvider` (`owo.providers.anthropic`), `OpenAIProvider`
  (`owo.providers.openai`), and `OpenRouterProvider` (`owo.providers.openrouter`)
  ship with the package; install extras with `pip install 'owo-parse[anthropic]'`,
  `[openai]`, or `[openrouter]`.
- `BaseProvider.complete_messages(user_text)` — new preferred extension point
  that gives providers access to the user text directly so they can pass the
  system prompt via the SDK's native system-message field. The default
  implementation falls back to `complete()` for custom providers that only
  implement the single-string interface.
- `owo._prompt` module: `SYSTEM_PROMPT` (rich instruction block with eight
  few-shot examples across all five languages and all intents) and
  `build_user_message()`. Custom providers can import `SYSTEM_PROMPT` directly.
- All three built-in providers use `temperature=0` by default for deterministic
  JSON output; overridable via the `temperature` constructor argument.
- Graceful handling of malformed LLM output in `result_from_provider_json`:
  invalid JSON now returns `intent=unknown` with a `bad_provider_output` flag
  instead of raising `JSONDecodeError`.
- Eval fixture corpus: 55+ cases across all five languages covering transfers,
  balance checks, Naija numerics, code-switching (bank name injection), and
  LLM-required intents (`buy_airtime`, `buy_data`, `bill_pay`, `crypto_sell`).
- Provider unit tests (`tests/test_providers.py`) using `sys.modules` mocking —
  no real API keys required.

### Changed

- Offline heuristic fallback intent is `unknown` (was `balance_check`) when
  no rule matches; `needs_llm_provider` flag is always set on fallback.
- `language_detected` is now a typed `Language` enum value — string comparisons
  (`result.language_detected == "en"`) still work via `str, Enum`.
- `parse()` now runs the heuristic first in all cases. When a provider is
  supplied, it is only called for inputs that the heuristic cannot handle
  (i.e. `needs_llm_provider` in `result.flags`). Previously, a provider call
  was always made when a provider was passed.
