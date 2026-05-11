# owo

**Nigerian-language financial intent parser.**

`owo` takes a free-form financial instruction in English, Pidgin, Yoruba, Hausa, or Igbo — and returns structured JSON that any payment backend can consume.

```python
from owo import parse

result = parse("Send 20k to Mama")

# {
#   "intent": "transfer",
#   "amount": 20000,
#   "currency": "NGN",
#   "recipient": "Mama",
#   "confidence": 0.97
# }
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
    intent: str                    # transfer | bill_pay | buy_airtime | buy_data | crypto_sell | balance_check
    amount: float | None
    currency: str                  # always "NGN" for now
    recipient: str | None
    account_number: str | None
    bank: str | None
    service: str | None            # MTN | DSTV | EKEDC | ...
    language_detected: str         # en | pcm | yo | ha | ig
    confidence: float              # 0.0 – 1.0
    flags: list[str]               # ["missing_amount", "ambiguous_recipient", ...]
    raw: dict                      # full LLM response for debugging
```

---

## Configuration

By default, `parse()` runs a **small offline heuristic** for a handful of common
English patterns so you can develop and run tests without API keys. For full
multilingual coverage, pass a **provider** that implements `BaseProvider` from
`owo` (for example Anthropic or OpenAI behind your own wrapper).

Swap in a provider via the abstraction:

```python
from owo import parse
from owo.providers import OpenAIProvider

result = parse(
    "Send 20k to Mama",
    provider=OpenAIProvider(model="gpt-4o")
)
```

Or bring your own:

```python
from owo.providers import BaseProvider

class MyProvider(BaseProvider):
    def complete(self, prompt: str) -> str:
        # call whatever you want here
        ...
```

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