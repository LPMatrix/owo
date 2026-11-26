# Contributing to owo

Thank you for helping improve **owo**, the Nigerian-language financial intent parser. This document explains how to contribute effectively.

## What we need most

- **Eval fixtures** in **Yoruba**, **Hausa**, and **Igbo** — high-quality, realistic phrases are hard to source; curated examples materially improve quality.
- **Edge cases** for code-switching and Naija numerics (`5k`, `half a milli`, bank names, meter numbers, etc.).
- **Native-speaker review** of the Pidgin, Hausa, Yoruba and Igbo word lists (see below).
- **Bug reports** with the exact input string, the provider/model if you passed one, and what you expected vs. what you got.

---

## Code of conduct

Please read [CODE_OF_CONDUCT.md](./CODE_OF_CONDUCT.md). Harassment and
discrimination are not tolerated.

---

## Development setup

1. **Python 3.11+** is required (see the README).
2. Clone the repository and install in editable mode with dev (and eval) extras:

   ```bash
   pip install -e ".[dev,eval]"
   ```

   You can also use `uv pip install -e ".[dev,eval]"` if you use [uv](https://github.com/astral-sh/uv).

3. Lint, test, and run the eval runner before opening a PR:

   ```bash
   ruff check src tests
   pytest
   python -m owo.eval
   ```

---

## Contributing eval / test fixtures

Fixtures are the primary way to lock in behavior across languages and intents. Prefer **realistic user phrasing** over synthetic textbook sentences.

### Fixture shape (recommended)

Each fixture should tie a **single user utterance** to **expected structured fields** that align with `OwoResult` (see README). A minimal YAML example:

```yaml
id: transfer_pidgin_001
input: "Abeg send 5k to Chidi, GTBank"
expected:
  intent: transfer
  language_detected: pcm
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

Use the same field names the library exposes (`intent`, `amount`, `currency`, `recipient`, `account_number`, `bank`, `service`, `flags`, etc.). Valid `intent` values include `unknown` when asserting heuristic fallback or unresolved input. Only the fields you list under `expected` are compared.

For input the offline rules don't handle (bill payments, airtime, data, crypto), add `requires_provider: true`. The runner skips those fixtures unless you pass `--provider module:ClassName`.

### Conventions

- **One primary intent per fixture** — if a sentence could mean two things, either split into two fixtures with `notes`, or mark with `flags` that reflect real product behavior.
- **Stable IDs** — use a short prefix (`transfer_`, `bill_`, `airtime_`, …) plus language code and a serial number.
- **No secrets** — do not use real account numbers, phone numbers, or personal names of private individuals; use obviously synthetic values (`08012345678`, `Ahmad`, `meter 4512345678`).
- **Spelling variants** — if users commonly spell a service or bank several ways, add separate fixtures rather than overloading one.

### Where to put files

Ship eval YAML fixtures under **`src/owo/eval/fixtures/`** (see the files
there; each holds one fixture or a list). Unit tests live in **`tests/`**. If you
are unsure where a new corpus belongs, open an issue or note it in your PR
description.

---

## Word lists and normalization maps

The offline rules and their word lists live in [`src/owo/_heuristic.py`](./src/owo/_heuristic.py):

| Name | What it holds |
| ---- | ------------- |
| `_VARIANT_MAP` | Texting abbreviations and their full spelling |
| `_LANGUAGE_MARKERS` | Weighted words that identify each language |
| `_HA_NUM_WORDS`, `_IG_NUM_WORDS` | Number words used in amounts |
| `_TRAILING_FILLERS` | Words trimmed from the end of a recipient |
| `_NOT_NAME_WORDS` | Words showing that captured text is more than a name |
| `_TITLES`, `_RELATIONS` | Words that can introduce a recipient ("Uncle", "my mum") |
| `_NOT_TYPOS` | Real words that must never be corrected into a transfer verb |

When adding or editing one:

1. Prefer **small, narrow** changes — a payment parser should hand a sentence to a provider rather than guess.
2. Add a **fixture** or test showing the change helps. For amount or recipient rules, also test what must still be handed over (see `tests/test_safety.py`).
3. Document **non-obvious** entries in a comment or in `notes` on the related fixture.
4. If you add a transfer verb, add the real words close to it to `_NOT_TYPOS`.

---

## Provider contributions

Custom LLM and STT providers are welcome. For a new first-party provider in-tree:

- Match the **`BaseProvider`** contract (for LLM) or **`BaseSTTProvider`** contract
  (for speech-to-text) used by `parse()` and `parse_audio()` respectively.
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
- **Provider/model**, if you passed one (offline parsing uses none).
- **Actual JSON** (or redacted `raw`) vs. **expected** behavior.

Replace real names, phone numbers and account numbers with made-up ones. Report
security problems privately, as described in [SECURITY.md](./SECURITY.md).

---

## License

By contributing, you agree that your contributions will be licensed under the same terms as the project (**MIT**), unless stated otherwise in a particular file or contribution.

---

Questions are welcome in issues or PR threads. Thanks again for improving financial NLU for Nigerian languages.
