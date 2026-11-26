# owo

[![PyPI](https://img.shields.io/pypi/v/owo-parse)](https://pypi.org/project/owo-parse/)
[![Python](https://img.shields.io/pypi/pyversions/owo-parse)](https://pypi.org/project/owo-parse/)
[![CI](https://github.com/LPMatrix/owo/actions/workflows/ci.yml/badge.svg)](https://github.com/LPMatrix/owo/actions/workflows/ci.yml)
[![Coverage](https://codecov.io/gh/LPMatrix/owo/branch/main/graph/badge.svg)](https://codecov.io/gh/LPMatrix/owo)
[![Downloads](https://img.shields.io/pypi/dm/owo-parse)](https://pypi.org/project/owo-parse/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

**Nigerian-language financial intent parser.**

> **Alpha software.** `owo` can misread a message. Confirm the amount and
> recipient with your user before moving money. See
> [Safety and privacy](#safety-and-privacy).

`owo` takes a free-form financial instruction in English, Pidgin, Yoruba, Hausa, or Igbo — and returns structured JSON that any payment backend can consume.

```python
from owo import parse

result = parse("Send 20k to Mama")

# OwoResult(intent='transfer', amount=20000.0, currency='NGN', recipient='Mama',
#           field_confidence={'intent': 0.95, 'recipient': 0.9,
#                             'language_detected': 0.88, 'amount': 0.97}, flags=[], ...)
```

---

## Why owo?

Nigerian fintech products that want a conversational layer have to solve the same hard problem: users don't speak in structured commands. They say *"abeg send 5k to Chidi"*, or *"Aika dubu goma zuwa ga Ahmad"*, or *"biya wutar lantarki"*. Most NLU libraries weren't built for this. `owo` was. Common transfers like the first two parse offline; a bill payment like the third needs a [provider](#configuration).

It handles:

- **Code-switching** — Pidgin and English in one sentence ("Abeg send 5k to Chidi, GTBank")
- **Naija numerics** — `5k`, `half a milli`, `dubu goma`, `nde ise`
- **Intent ambiguity** — flags underspecified fields rather than guessing
- **Backend agnosticism** — plug in your own LLM provider

---

## Installation

```bash
pip install owo-parse
```

Requires Python 3.11+.

---

## Quickstart

```python
from owo import parse

# English
parse("Send half a milli to Kemi")      # transfer, 500000.0, Kemi

# Pidgin
parse("Abeg send 5k to Chidi, GTBank")  # transfer, 5000.0, Chidi, GTBank

# Yoruba
parse("Fi ₦5,000 ranṣẹ si Tunde")       # transfer, 5000.0, Tunde

# Hausa
parse("Aika dubu goma zuwa ga Ahmad")   # transfer, 10000.0, Ahmad

# Igbo
parse("Zipụ ego nde ise nye Emeka")     # transfer, 5000000.0, Emeka

# Balance check
parse("How much I get?")                # balance_check
```

All of these run offline. Bill payments, airtime, data and crypto need a
[provider](#configuration).

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
    field_confidence: dict[str, float]  # per-field certainty, e.g. {"amount": 0.97, "recipient": 0.9}
    flags: list[str]               # ["missing_amount", "ambiguous_recipient", ...]
    raw: dict                      # parser metadata for debugging
```

`field_confidence` scores each field on its own, so a shaky result tells you
*which* field to distrust rather than collapsing to one vague number. Only the
fields that are in play for the detected intent are scored (`intent` and
`language_detected` always are). Two helpers come with it:

```python
result.confidence_for("amount", default=0.0)  # one field's score
result.min_confidence                          # weakest field — a single go/no-go gate
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

provider = AnthropicProvider()  # or OpenAIProvider() / OpenRouterProvider()

# These fall outside the offline rule set, so the provider handles them
parse("Buy 2GB data for 08012345678 on MTN", provider=provider)
parse("Abeg top up my light, meter number 4512345678", provider=provider)
parse("Jẹ kí n san ₦5,000 fún DSTV mi", provider=provider)
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

result.amount                       # None
result.flags                        # ["missing_amount"]
result.field_confidence             # {"intent": 0.95, "recipient": 0.9,
                                    #  "language_detected": 0.88, "amount": 0.2}
result.confidence_for("amount")     # 0.2  ← the field to ask about
result.confidence_for("recipient")  # 0.9  ← keep as-is
result.min_confidence               # 0.2
```

Use `field_confidence` (or `min_confidence` for a single gate) together with
`flags` to decide whether — and about *which field* — to ask the user for
clarification before passing the result downstream.

### When owo won't guess

The offline rules accept a transfer only when the text after "to" (or its
equivalent) looks like a name by itself. Anything else returns `unknown`, with
no amount or recipient, so a provider can read the whole sentence:

```python
result = parse("send 5k to Chidi tomorrow")

result.intent                      # "unknown"
result.recipient                   # None
result.flags                       # ["needs_llm_provider", "ambiguous_recipient"]
result.raw["unparsed_recipient"]   # "Chidi tomorrow"
```

This covers extra clauses, account numbers, banks written without a comma and
several words in lower case. Other reasons are `invalid_amount` (zero or not a
finite number) and `input_too_long` (over 500 characters).

These checks use word lists and capitalisation, so they can't catch every
sentence. For example, extra capitalised words can be read as part of a name.

Provider replies are validated too. A value of the wrong type, or an amount that
isn't a positive number, is dropped and flagged `invalid_<field>`; a reply that
isn't a JSON object, or has no valid intent, is flagged `bad_provider_output`.

---

## Safety and privacy

### Before money moves

`owo` turns text into fields. It does not check that a recipient exists, look up
balances or enforce limits. Your application should:

- show the amount, recipient and bank to the user and get explicit confirmation,
  however high the confidence;
- match the recipient to an account using records you trust;
- apply its own amount limits, since `owo` sets no maximum;
- stop and ask the user when a result carries any flag.

`field_confidence` is not a measured accuracy. Offline scores are set by the
rules; with a provider, they are whatever the model reports. A provider can also
return a well-formed but wrong answer.

### What leaves your system

| You call                              | What is sent                                                  |
| ------------------------------------- | ------------------------------------------------------------- |
| `parse(text)`                         | Nothing. The offline rules make no network calls              |
| `parse(text, provider=...)`           | The full text, to that provider, if the offline rules can't handle it |
| `parse_audio(..., stt_provider=...)`  | The audio, to the speech-to-text service (OpenAI for `WhisperProvider`), then the transcript as above |

Check each provider's data terms and the privacy law that applies to your users.

`result.raw` can contain the user's text and the provider's reply, including
names and account numbers. Redact it before logging or storing it.

---

## Supported intents


| Intent          | Example                           | Offline         |
| --------------- | --------------------------------- | --------------- |
| `transfer`      | "Send 20k to Mama"                | Common patterns |
| `bill_pay`      | "Pay my DSTV, smart card 1234567" | Needs provider  |
| `buy_airtime`   | "Recharge 500 naira on Airtel"    | Needs provider  |
| `buy_data`      | "Buy 5GB MTN data for my line"    | Needs provider  |
| `crypto_sell`   | "Sell 50 USDT"                    | Needs provider  |
| `balance_check` | "How much I get?"                 | Common patterns |

`parse()` returns `unknown` with the `needs_llm_provider` flag when the offline
rules can't classify an input and no provider is passed.


---

## Supported languages


| Code  | Language        |
| ----- | --------------- |
| `en`  | English         |
| `pcm` | Nigerian Pidgin |
| `yo`  | Yoruba          |
| `ha`  | Hausa           |
| `ig`  | Igbo            |


Offline, `owo` picks the language from the marker words in each sentence and handles mixed-language input that fits a supported pattern. Pass a provider for other code-switched input.

---

## Voice input

`owo` can parse voice notes and audio directly via `parse_audio()`. Install the
voice extra to get the Whisper STT provider:

```bash
pip install 'owo-parse[voice]'
```

```python
from owo import parse_audio
from owo.providers.whisper import WhisperProvider

with open("voice_note.ogg", "rb") as f:
    result = parse_audio(
        f.read(),
        stt_provider=WhisperProvider(),  # reads OPENAI_API_KEY from env
    )

# For a voice note transcribed as "Abeg send 5k to Tunde":
# result.intent    → "transfer"
# result.amount    → 5000.0
# result.recipient → "Tunde"
```

The flow is: **audio bytes → Whisper transcription → `parse()`**. The LLM
fallback still applies — pass `provider=` alongside `stt_provider=` if you need
it for complex intents.

**Language hints** — Whisper accepts a language code to improve accuracy. Pass
the expected language for best results on accented or tonal speech:

```python
WhisperProvider(language="yo")   # Yoruba
WhisperProvider(language="ha")   # Hausa
WhisperProvider(language="ig")   # Igbo
WhisperProvider(language="en")   # English
# Omit language= for Nigerian Pidgin (auto-detect works best)
```

**Bring your own STT** — any backend works by subclassing `BaseSTTProvider`:

```python
from owo import BaseSTTProvider

class GoogleSTTProvider(BaseSTTProvider):
    def transcribe(self, audio: bytes, *, filename: str = "audio.mp3") -> str:
        ...  # call Google Speech-to-Text here
```

---

## Running the eval suite

`owo` ships with a benchmark suite of curated test fixtures across all five languages:

```bash
pip install 'owo-parse[eval]'
python -m owo.eval
```

Results are printed per-language, per-intent, with a breakdown of field-level accuracy.

---

## Project status

`owo` is alpha software, and behaviour or the result format can change between
minor releases. Version 0.3.0, for example, replaced the single `confidence`
score with `field_confidence`.

[CHANGELOG.md](./CHANGELOG.md) lists released and unreleased changes. Suggest
what should come next in the
[issue tracker](https://github.com/LPMatrix/owo/issues).

---

## Contributing

Contributions welcome — especially test fixtures in Yoruba, Hausa, and Igbo, which are the hardest to source.

See [CONTRIBUTING.md](./CONTRIBUTING.md) for the fixture format and where the language word lists live.

This project follows the [Contributor Covenant](./CODE_OF_CONDUCT.md). Security
disclosures: [SECURITY.md](./SECURITY.md). Changes are summarized in
[CHANGELOG.md](./CHANGELOG.md).

---

## License

[MIT](./LICENSE)