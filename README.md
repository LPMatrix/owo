# owo

[![PyPI](https://img.shields.io/pypi/v/owo-parse)](https://pypi.org/project/owo-parse/)
[![Python](https://img.shields.io/pypi/pyversions/owo-parse)](https://pypi.org/project/owo-parse/)
[![CI](https://github.com/LPMatrix/owo/actions/workflows/ci.yml/badge.svg)](https://github.com/LPMatrix/owo/actions/workflows/ci.yml)
[![Coverage](https://codecov.io/gh/LPMatrix/owo/branch/main/graph/badge.svg)](https://codecov.io/gh/LPMatrix/owo)
[![Downloads](https://img.shields.io/pypi/dm/owo-parse)](https://pypi.org/project/owo-parse/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

**Nigerian-language financial intent parser.**

`owo` takes a free-form financial instruction in English, Pidgin, Yoruba, Hausa, or Igbo — and returns structured JSON that any payment backend can consume.

```python
from owo import parse

result = parse("Send 20k to Mama")

# OwoResult(intent='transfer', amount=20000.0, currency='NGN',
#           recipient='Mama', confidence=0.85, flags=[], ...)
```

---

## Why owo?

Nigerian fintech products that want a conversational layer have to solve the same hard problem: users don't speak in structured commands. They say *"abeg send 5k to Chidi"*, or *"jẹ kí n san owo ina mi"*, or *"biya wutar lantarki"*. Most NLU libraries weren't built for this. `owo` was.

It handles:

- **Code-switching** — mid-sentence language mixing ("Send am 5k abeg, GTBank")
- **Naija numerics** — `5k`, `2 bags`, `half a milli`
- **Intent ambiguity** — flags underspecified fields rather than guessing
- **Backend agnosticism** — plug in your own LLM provider

---

## Installation

```bash
pip install owo-parse
```

Requires Python 3.10+.

---

## Quickstart

```python
from owo import parse

# English
parse("Buy 2GB data for 08012345678 on MTN")

# Pidgin
parse("Abeg top up my light, meter number 4512345678")

# Yoruba
parse("Jẹ kí n san ₦5,000 fún DSTV mi")

# Hausa
parse("Aika dubu goma zuwa ga Ahmad")

# Igbo
parse("Zipụ ego nde ise nye Emeka")
```

Every call returns an `OwoResult`:

```python
@dataclass
class OwoResult:
    intent: str                    # transfer | bill_pay | buy_airtime | buy_data | crypto_sell | balance_check | unknown
    amount: float | None
    currency: str                  # always "NGN" for now
    recipient: str | None
    account_number: str | None
    bank: str | None
    service: str | None            # MTN | DSTV | EKEDC | ...
    language_detected: str         # en | pcm | yo | ha | ig
    confidence: float              # 0.0 – 1.0
    flags: list[str]               # ["missing_amount", "ambiguous_recipient", ...]
    raw: dict                      # parser metadata for debugging
```

---

## Configuration

By default, `parse()` runs an **offline heuristic** covering common transfer and
balance patterns across all five supported languages (English, Pidgin, Yoruba,
Hausa, and Igbo). No API key needed. Inputs that fall outside the heuristic's
rule set return `intent: "unknown"` with `needs_llm_provider` in `flags` — pass
a provider to handle those cases.

```python
# Offline — works for common patterns in all five languages
parse("Abeg send 5k to Chidi, GTBank")
parse("Aika dubu goma zuwa ga Ahmad")
parse("Send half a milli to Kemi")
```

To handle complex or ambiguous inputs, plug in an LLM provider. Three providers
ship with the package:

```bash
pip install 'owo-parse[anthropic]'   # Anthropic
pip install 'owo-parse[openai]'      # OpenAI
pip install 'owo-parse[openrouter]'  # OpenRouter (access to 200+ models)
```

```python
from owo import parse
from owo.providers.anthropic import AnthropicProvider   # ANTHROPIC_API_KEY
from owo.providers.openai import OpenAIProvider         # OPENAI_API_KEY
from owo.providers.openrouter import OpenRouterProvider # OPENROUTER_API_KEY

result = parse(
    "Buy 2GB data for 08012345678 on MTN",
    provider=AnthropicProvider(),  # or OpenAIProvider() / OpenRouterProvider()
)
```

The heuristic always runs first — the provider is only called when the input falls
outside the rule set (i.e. `needs_llm_provider` is in `result.flags`). This keeps
costs low for common transfer and balance patterns.

Or bring your own by subclassing `BaseProvider`:

```python
from owo import BaseProvider

class MyProvider(BaseProvider):
    def complete(self, prompt: str) -> str:
        # Fallback — called when complete_messages() is not overridden.
        # Receives the full system + user prompt as a single string.
        ...

    def complete_messages(self, user_text: str) -> str:
        # Preferred override — gives you the user text directly so you can
        # pass the system prompt via your SDK's native system-message field.
        response = my_llm_client.chat(
            system=MY_SYSTEM_PROMPT,   # use owo._prompt.SYSTEM_PROMPT
            user=user_text,
        )
        return response.text
```

`SYSTEM_PROMPT` from `owo._prompt` contains the full instruction block with few-shot examples across all five languages — use it as-is or extend it.

---

## Handling ambiguity

`owo` never silently fills in missing fields. If it can't determine the amount, it says so:

```python
result = parse("Send money to Tunde")

result.amount        # None
result.flags         # ["missing_amount"]
result.confidence    # 0.61
```

Use `confidence` and `flags` to decide whether to ask the user for clarification before passing the result downstream.

---

## Supported intents


| Intent          | Example                           |
| --------------- | --------------------------------- |
| `transfer`      | "Send 20k to Mama"                |
| `bill_pay`      | "Pay my DSTV, smart card 1234567" |
| `buy_airtime`   | "Recharge 500 naira on Airtel"    |
| `buy_data`      | "Buy 5GB MTN data for my line"    |
| `crypto_sell`   | "Sell 50 USDT"                    |
| `balance_check` | "How much I get?"                 |
| `unknown`       | Heuristic could not classify; use `flags` (`needs_llm_provider`) or an LLM provider |


---

## Supported languages


| Code  | Language        |
| ----- | --------------- |
| `en`  | English         |
| `pcm` | Nigerian Pidgin |
| `yo`  | Yoruba          |
| `ha`  | Hausa           |
| `ig`  | Igbo            |


Mixed-language input (code-switching) is handled automatically — `owo` detects the dominant language and resolves cross-language entities.

---

## Running the eval suite

`owo` ships with a benchmark suite of curated test fixtures across all five languages:

```bash
pip install owo-parse[eval]
python -m owo.eval
```

Results are printed per-language, per-intent, with a breakdown of field-level accuracy.

---

## Roadmap


| Version | Focus                                                 |
| ------- | ----------------------------------------------------- |
| `v0.1`  | Core intent + entity extraction (English + Pidgin)    |
| `v0.2`  | Full multilingual support (Yoruba, Hausa, Igbo)       |
| `v0.3`  | Confidence scores, ambiguity flags, graceful fallback |
| `v1.0`  | Provider abstraction, eval suite, docs, OSS-ready     |


---

## Contributing

Contributions welcome — especially test fixtures in Yoruba, Hausa, and Igbo, which are the hardest to source.

See [CONTRIBUTING.md](./CONTRIBUTING.md) for the fixture format and how to add a new language normalization map.

This project follows the [Contributor Covenant](./CODE_OF_CONDUCT.md). Security
disclosures: [SECURITY.md](./SECURITY.md). Changes are summarized in
[CHANGELOG.md](./CHANGELOG.md).

---

## License

[MIT](./LICENSE)