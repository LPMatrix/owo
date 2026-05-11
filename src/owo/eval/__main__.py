from __future__ import annotations

from importlib import resources
from typing import Any

import yaml

from owo import parse
from owo.result import OwoResult


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
        if isinstance(data, dict):
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
        got = actual.get(key)
        if not _same(exp, got):
            mismatches.append(f"{key}: expected {exp!r}, got {got!r}")
    return mismatches


def main() -> int:
    fixtures = _load_fixtures()
    if not fixtures:
        print("No YAML fixtures found under owo.eval.fixtures.")
        return 0

    failed = 0
    for fx in fixtures:
        fx_id = fx.get("id", "<no id>")
        inp = fx.get("input")
        if not isinstance(inp, str):
            print(f"[skip] {fx_id}: missing string 'input'")
            continue
        expected = fx.get("expected")
        if not isinstance(expected, dict):
            print(f"[skip] {fx_id}: missing mapping 'expected'")
            continue

        result = parse(inp)
        actual = _as_dict(result)
        mismatches = _compare(expected, actual)
        if mismatches:
            failed += 1
            print(f"FAIL {fx_id}")
            for m in mismatches:
                print(f"  - {m}")
        else:
            print(f"ok   {fx_id}")

    if failed:
        print(f"\n{failed} fixture(s) failed.")
        return 1
    print(f"\nAll {len(fixtures)} fixture(s) passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
