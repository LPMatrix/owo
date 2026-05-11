# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

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
- `AnthropicProvider` in `owo.providers_anthropic`; install with
  `pip install 'owo-parse[anthropic]'`.
- Eval fixture corpus: 40+ cases across all five languages covering transfers,
  balance checks, Naija numerics, and code-switching (bank name injection).

### Changed

- Offline heuristic fallback intent is `unknown` (was `balance_check`) when
  no rule matches; `needs_llm_provider` flag is always set on fallback.
- `language_detected` is now a typed `Language` enum value — string comparisons
  (`result.language_detected == "en"`) still work via `str, Enum`.
