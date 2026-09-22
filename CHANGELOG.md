# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed

- **Heuristic silently corrupted the recipient on any trailing word.** Every
  transfer pattern's `(.+)$` capture ran to the end of the string, so filler
  after the name — "send 20k to mama **pls**", "...mama **now**" — became part
  of `recipient` with no flag and high confidence. Trailing filler (`pls`,
  `please`, `now`, `abeg`, `sha`, `jare`, `biko`) is now trimmed before the
  recipient is returned.

### Added

- The heuristic strips common leading filler/politeness phrases ("hey",
  "pls", "can you", "i want to", "kindly") before matching, so natural
  phrasing like "hey abeg send 20k to mama" or "can you send 20k to my mum"
  now resolves instead of falling through to `unknown`.
- `abeg` tolerates a following comma ("Abeg, send 5k give Chidi").
- The `Nk` amount patterns accept an optional trailing "naira" ("transfer 20k
  naira to mama's account").
- A connector-less object-first fallback for English: "send mama 20k" (no
  "to"/"give"). Scored lower (`intent`/`recipient` confidence) than a
  connector-anchored match, since there's no connector word to anchor the
  recipient boundary on.
- `_EN_BALANCE` recognizes a couple more natural phrasings: "how much is in
  my account", "what's in my account".
- `OwoResult.confidence_for` and `min_confidence` reflect the above: a
  trimmed-but-clean recipient scores slightly lower than an untouched one, and
  the object-first fallback scores lower than a connector-anchored match —
  same "explicit vs. inferred" scale the per-field scores already use.

A verb-less input ("20k to mama") is still an intentional miss — too
ambiguous to guess without a provider. Object-first matching is English-only
for now; the other four languages keep their existing connector-anchored
patterns.

### Changed

- **Rewrote the heuristic matching engine.** `_heuristic.py` previously had
  ~30 duplicated, hand-anchored regex blocks (one per language × amount-shape
  combination), and language was decided by a hardcoded try-pcm-then-ha-then-
  yo-then-ig-then-en cascade. Replaced with:
  - A **shared amount-shape library** (`_extract_amount_k`,
    `_extract_amount_plain`, `_extract_amount_half_milli`,
    `_extract_amount_milli`, `_extract_amount_dubu_word`,
    `_extract_amount_dubu_n`) that each language's grammar composes from,
    instead of re-deriving the same amount regex per language.
  - A **generic transfer grammar** (`_match_transfer`) parameterized by
    verb/connector regex + amount shapes + an optional pre-amount token
    (Igbo's "ego"), so each language is now a short declarative call
    (`_match_en_transfer`, `_match_ha_transfer`, `_match_yo_transfer`,
    `_match_ig_transfer`) instead of 5-7 hand-written full-line regexes.
    Pidgin keeps its own wrapper (`_match_pcm_transfer`) since its
    disambiguation rule — leading "abeg" OR a "give" connector OR trailing
    "am" — is a genuine three-way disjunction the generic template doesn't
    fit.
  - **Marker-scored language ranking** (`_score_languages`,
    `_ranked_languages`) replacing the fixed cascade order: each language has
    a weighted marker set (Hausa's "aika"/"dubu" score high; English's
    "send"/"transfer" score low since they double as pidgin's verbs too),
    and languages are tried in the order their evidence in *this* utterance
    ranks them — not a hardcoded position.
  - **Computed `language_detected` confidence** (`_language_confidence`)
    replacing the static per-language lookup table — blends each language's
    baseline reliability with how dominant its marker evidence was relative
    to competing languages in the specific input, so a clean unambiguous
    sentence now scores higher than one with cross-language noise.
  - **Normalization/typo-tolerance pass** ahead of matching:
    `_canonicalize_variants` folds a small set of texting abbreviations
    ("pls"/"plz"/"plse" → "please", "abg" → "abeg", "nw" → "now") to a
    canonical spelling before anything else runs (inspired by the finding in
    "Modeling Orthographic Variation Improves NLP Performance for Nigerian
    Pidgin", arXiv:2404.18264, that canonicalizing spelling variation before
    matching helps); `_fuzzy_correct_leading_token` typo-corrects the leading
    verb/marker token against the closed vocabulary via stdlib `difflib`
    (cutoff 0.8, single-token blast radius only — e.g. "trasfer 20k to mama"
    now resolves). No new dependency.
  - `OwoResult.field_confidence` and all pattern outcomes are unchanged for
    every existing test/fixture; this is an internal architecture change, not
    a behavior change for previously-covered input (verified against the
    full 89-test/41-fixture suite plus an ad hoc adversarial/false-positive
    check).

---

## [0.3.0] — 2026-09-01

### Added

- **Per-field confidence**: `OwoResult.field_confidence` — a `dict[str, float]`
  mapping each scored field to its own 0.0–1.0 certainty, so a shaky parse points
  at *which* field to distrust instead of collapsing to one number. Only fields
  relevant to the detected intent are scored (`intent` and `language_detected`
  always are).
- `OwoResult.confidence_for(field, default=0.0)` and `OwoResult.min_confidence`
  helpers.
- Eval fixtures may assert `field_confidence` with numeric comparators —
  `">=0.9"`, `"<0.3"`, `"0.8..1.0"`, or a bare number for exact match.

### Changed

- **BREAKING**: removed the scalar `OwoResult.confidence`; use `field_confidence`
  or `min_confidence`.
- **BREAKING**: the provider JSON contract now expects a `field_confidence`
  object instead of a `confidence` float. `SYSTEM_PROMPT` and its few-shot
  examples are updated. Providers that still emit a bare `confidence` scalar are
  handled for now by spreading that value across the populated fields.
- The heuristic derives the `missing_amount` / `missing_recipient` flags from the
  same per-field scores it emits, so a flag and its field score can no longer
  drift apart.
- Eval suite tracks `field_confidence` instead of `confidence`.

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
