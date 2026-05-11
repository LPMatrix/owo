from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from importlib import resources
from typing import Any

import yaml

from owo import parse
from owo.schema import OwoResult

_TRACKED_FIELDS = [
    "intent",
    "amount",
    "currency",
    "recipient",
    "account_number",
    "bank",
    "service",
    "language_detected",
    "confidence",
    "flags",
]


@dataclass
class _FixtureResult:
    fx_id: str
    passed: bool
    mismatches: list[str]
    intent: str
    language: str
    expected: dict[str, Any]
    actual: dict[str, Any]


def _as_dict(result: OwoResult) -> dict[str, Any]:
    return {
        "intent": result.intent,
        "amount": result.amount,
        "currency": result.currency,
        "recipient": result.recipient,
        "account_number": result.account_number,
        "bank": result.bank,
        "service": result.service,
        "language_detected": result.language_detected,
        "confidence": result.confidence,
        "flags": list(result.flags),
    }


def _load_fixtures() -> list[dict[str, Any]]:
    root = resources.files("owo.eval") / "fixtures"
    if not root.is_dir():
        return []
    items: list[dict[str, Any]] = []
    for path in sorted(root.iterdir(), key=lambda p: p.name):
        if path.suffix.lower() not in {".yaml", ".yml"}:
            continue
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            items.extend(d for d in data if isinstance(d, dict))
        elif isinstance(data, dict):
            items.append(data)
    return items


def _same(expected: Any, actual: Any) -> bool:
    if isinstance(expected, (int, float)) and isinstance(actual, (int, float)):
        return float(expected) == float(actual)
    if isinstance(expected, list) and isinstance(actual, list):
        return len(expected) == len(actual) and all(
            _same(e, a) for e, a in zip(expected, actual, strict=True)
        )
    return expected == actual


def _compare(expected: dict[str, Any], actual: dict[str, Any]) -> list[str]:
    mismatches: list[str] = []
    for key, exp in expected.items():
        if not _same(exp, actual.get(key)):
            mismatches.append(f"{key}: expected {exp!r}, got {actual.get(key)!r}")
    return mismatches


def _run_fixture(fx: dict[str, Any]) -> _FixtureResult | None:
    fx_id = fx.get("id", "<no id>")
    inp = fx.get("input")
    if not isinstance(inp, str):
        print(f"[skip] {fx_id}: missing string 'input'")
        return None
    expected = fx.get("expected")
    if not isinstance(expected, dict):
        print(f"[skip] {fx_id}: missing mapping 'expected'")
        return None

    result = parse(inp)
    actual = _as_dict(result)
    mismatches = _compare(expected, actual)
    return _FixtureResult(
        fx_id=fx_id,
        passed=not mismatches,
        mismatches=mismatches,
        intent=result.intent.value,
        language=result.language_detected.value,
        expected=expected,
        actual=actual,
    )


def _print_summary(results: list[_FixtureResult]) -> None:
    total = len(results)
    n_passed = sum(1 for r in results if r.passed)
    n_failed = total - n_passed

    sep = "─" * 52
    print(f"\n{sep}")
    verdict = "All passed." if n_failed == 0 else f"{n_failed} fixture(s) failed."
    print(f"Results: {n_passed} passed, {n_failed} failed  ({total} total)  {verdict}")

    by_intent: dict[str, list[_FixtureResult]] = defaultdict(list)
    by_lang: dict[str, list[_FixtureResult]] = defaultdict(list)
    field_hits: dict[str, int] = defaultdict(int)
    field_total: dict[str, int] = defaultdict(int)

    for r in results:
        by_intent[r.intent].append(r)
        by_lang[r.language].append(r)
        for f in _TRACKED_FIELDS:
            if f not in r.expected:
                continue
            field_total[f] += 1
            if _same(r.expected[f], r.actual.get(f)):
                field_hits[f] += 1

    print("\nBy intent:")
    for intent in sorted(by_intent):
        rs = by_intent[intent]
        p = sum(1 for r in rs if r.passed)
        print(f"  {intent:<22} {p}/{len(rs)}")

    print("\nBy language:")
    for lang in sorted(by_lang):
        rs = by_lang[lang]
        p = sum(1 for r in rs if r.passed)
        print(f"  {lang:<22} {p}/{len(rs)}")

    if field_total:
        print("\nField accuracy:")
        for f in _TRACKED_FIELDS:
            hits = field_hits.get(f, 0)
            tot = field_total.get(f, 0)
            if tot == 0:
                continue
            pct = 100 * hits // tot
            bar = "█" * (pct // 10) + "░" * (10 - pct // 10)
            print(f"  {f:<22} {hits:>3}/{tot:<3}  {bar}  {pct:>3}%")


def main() -> int:
    fixtures = _load_fixtures()
    if not fixtures:
        print("No YAML fixtures found under owo.eval.fixtures.")
        return 0

    results: list[_FixtureResult] = []
    for fx in fixtures:
        r = _run_fixture(fx)
        if r is None:
            continue
        results.append(r)
        if r.passed:
            print(f"ok   {r.fx_id}")
        else:
            print(f"FAIL {r.fx_id}")
            for m in r.mismatches:
                print(f"  - {m}")

    _print_summary(results)
    return 1 if any(not r.passed for r in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
