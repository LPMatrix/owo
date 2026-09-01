from __future__ import annotations

import pytest

from owo.eval.__main__ import _compare, _match_number


@pytest.mark.parametrize(
    ("spec", "actual", "expected"),
    [
        (0.95, 0.95, True),
        (0.95, 0.9, False),
        (">=0.9", 0.9, True),
        (">=0.9", 0.89, False),
        (">0.9", 0.9, False),
        ("<0.3", 0.2, True),
        ("<0.3", 0.3, False),
        ("<=0.3", 0.3, True),
        ("0.8..1.0", 0.9, True),
        ("0.8..1.0", 0.79, False),
        ("0.95", 0.95, True),
        ("==0.5", 0.5, True),
        (">=0.9", None, False),
        ("garbage", 0.5, False),
    ],
)
def test_match_number(spec, actual, expected) -> None:
    assert _match_number(spec, actual) is expected


def test_compare_field_confidence_only_checks_named_keys() -> None:
    expected = {"field_confidence": {"amount": ">=0.9", "intent": "0.9..1.0"}}
    actual = {"field_confidence": {"amount": 0.97, "intent": 0.95, "recipient": 0.1}}
    assert _compare(expected, actual) == []


def test_compare_field_confidence_flags_missing_key() -> None:
    expected = {"field_confidence": {"bank": ">=0.9"}}
    actual = {"field_confidence": {"amount": 0.97}}
    assert _compare(expected, actual) != []


def test_compare_field_confidence_flags_out_of_range() -> None:
    expected = {"field_confidence": {"amount": "<0.5"}}
    actual = {"field_confidence": {"amount": 0.97}}
    assert _compare(expected, actual) != []
