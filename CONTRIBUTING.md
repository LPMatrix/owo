# Contributing to owo

Thank you for helping improve **owo**, the Nigerian-language financial intent parser. This document explains how to contribute effectively.

## What we need most

- **Eval fixtures** in **Yoruba**, **Hausa**, and **Igbo** — high-quality, realistic phrases are hard to source; curated examples materially improve quality.
- **Edge cases** for code-switching and Naija numerics (`5k`, `half a milli`, bank names, meter numbers, etc.).
- **Bug reports** with the exact input string, provider/model (if not default), and what you expected vs. what you got.

---

## Code of conduct

Be respectful and constructive. Assume good intent. Harassment and discrimination are not tolerated.

---

## Development setup

1. **Python 3.10+** is required (see the README).
2. Clone the repository and install in editable mode with dev dependencies when they are defined in the project (for example):

   ```bash
   pip install -e ".[dev]"
   ```

   If the project uses another tool (e.g. `uv`), prefer the commands documented in `pyproject.toml` or CI workflows once present.

3. Run the test suite and eval before opening a PR:

   ```bash
   pytest
   pip install -e ".[eval]"
   python -m owo.eval
   ```

Adjust commands to match the repository once packaging and CI are in place.

---

## Contributing eval / test fixtures

Fixtures are the primary way to lock in behavior across languages and intents. Prefer **realistic user phrasing** over synthetic textbook sentences.

### Fixture shape (recommended)

Each fixture should tie a **single user utterance** to **expected structured fields** that align with `OwoResult` (see README). A minimal YAML example:

```yaml
id: transfer_pidgin_001
input: "Abeg send 5k to Chidi, GTBank"
language_hint: pcm          # optional; omit to rely on detector
expected:
  intent: transfer
  amount: 5000
  currency: NGN
  recipient: Chidi
  bank: GTBank
  account_number: null
  service: null
  flags: []                  # empty if nothing ambiguous
notes: "Code-switched bank name"
```

For cases where ambiguity is intentional:

```yaml
id: transfer_missing_amount_001
input: "Send money to Tunde"
expected:
  intent: transfer
  amount: null
  currency: NGN
  recipient: Tunde
  flags:
    - missing_amount
```

Use the same field names the library exposes (`intent`, `amount`, `currency`, `recipient`, `account_number`, `bank`, `service`, `flags`, etc.). If the eval runner compares only a subset of fields, document that in the fixture directory README when it exists.

### Conventions

- **One primary intent per fixture** — if a sentence could mean two things, either split into two fixtures with `notes`, or mark with `flags` that reflect real product behavior.
- **Stable IDs** — use a short prefix (`transfer_`, `bill_`, `airtime_`, …) plus language code and a serial number.
- **No secrets** — do not use real account numbers, phone numbers, or personal names of private individuals; use obviously synthetic values (`08012345678`, `Ahmad`, `meter 4512345678`).
- **Spelling variants** — if users commonly spell a service or bank several ways, add separate fixtures rather than overloading one.

### Where to put files

Follow the layout used in the repository (for example `tests/fixtures/` or `owo/eval/fixtures/`). If unsure, open an issue or ask in your PR description.

---

## Language normalization maps

Some preprocessing (digits, currency symbols, common abbreviations, tone-insensitive variants) may live in **normalization maps** per language (`en`, `pcm`, `yo`, `ha`, `ig`).

When adding or editing a map:

1. Prefer **small, reversible** normalizations — do not destroy information the model needs (e.g. do not strip all punctuation if it disambiguates amounts).
2. Add a **fixture** that proves the normalization helps (or that the model resolves the phrase correctly without harmful side effects).
3. Document **non-obvious** mappings in a comment or in `notes` on the related fixture.

If the project exposes a specific module path for maps, mirror existing naming and register new entries the same way neighboring languages do.

---

## Provider contributions

Custom `BaseProvider` implementations are welcome. For a new first-party provider in-tree:

- Match the **`BaseProvider`** contract used by `parse()`.
- Include **tests** that mock HTTP and assert prompt/response handling where applicable.
- Document **env vars** and defaults in the README or provider docstring.

---

## Pull requests

1. **One logical change per PR** — e.g. “Add Hausa bill_pay fixtures” or “Fix missing_amount flag for X” — easier to review and bisect.
2. **Describe motivation** — link an issue if one exists; otherwise a short paragraph is enough.
3. **Show results** — for fixture-only PRs, paste a snippet of `python -m owo.eval` before/after if you can.
4. **Keep diffs focused** — avoid unrelated formatting or drive-by refactors.

---

## Reporting issues

Include:

- **Exact input string** (copy-paste).
- **Python version** and **`owo` version** (or commit hash).
- **Provider/model** if not the default Anthropic setup.
- **Actual JSON** (or redacted `raw`) vs. **expected** behavior.

---

## License

By contributing, you agree that your contributions will be licensed under the same terms as the project (**MIT**), unless stated otherwise in a particular file or contribution.

---

Questions are welcome in issues or PR threads. Thanks again for improving financial NLU for Nigerian languages.
