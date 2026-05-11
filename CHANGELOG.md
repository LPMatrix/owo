# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Open source scaffolding: license, security policy, code of conduct, CI, and
  issue templates.
- Minimal `owo` package layout with `parse()`, `OwoResult`, and `BaseProvider`.
- Eval runner (`python -m owo.eval`) and sample fixture.
- Heuristic improvements: shared input normalization, `transfer` keyword and
  plain-`naira`/comma amounts, extra balance phrasings, `Intent.UNKNOWN` fallback
  (and invalid LLM `intent` strings map to `unknown`).
- Additional eval fixtures for transfers, balance phrasing, and unknown
  fallback.

### Changed

- Offline heuristic fallback intent is `unknown` (was `balance_check`) when
  no rule matches, still flagged with `needs_llm_provider`.
