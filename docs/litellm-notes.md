# LiteLLM ↔ Local AI Gateway

Working notes for the eventual article. Publishable blog is deferred.

## What an AI gateway does

An AI gateway sits between clients and model providers. It usually:

1. Exposes one stable API (often OpenAI-shaped)
2. Maps logical model names to real backends
3. Applies routing / fallbacks / retries
4. Runs callbacks (logging, spend, guardrails) around the call

## LiteLLM (high level)

LiteLLM’s proxy is the reference shape we mirrored:

| Piece | LiteLLM | This repo |
|---|---|---|
| API | `/v1/chat/completions` | same |
| Providers | OpenAI, Anthropic, Ollama, … | Ollama + local GPT-2 |
| Router | load / latency / cost / usage | **capability tiers** + **intent pins** |
| Callbacks | pre/post success/failure hooks | pre-call + post-call guardrails |
| Observability | spend logs, callbacks | `gateway_trace` on every response |

LiteLLM does **not** ship complexity-based or specialty-intent routing as a first-class default. Those are our teaching extensions — still living in the same “proxy decides, then calls a provider” pattern.

## Capability ladder (honest)

Ascending by real chat usefulness on this machine:

1. `gpt2-xl` — largest GPT-2, weakest instruct quality
2. `qwen2.5:0.5b` — small modern instruct
3. `qwen2.5:3b` — mid tier
4. `phi3:mini` — strongest local tier

Article point: **size ≠ smarts**. GPT-2 XL has ~1.5B params but loses to modern smaller instruct models.

## Intent specialty examples

Configured in `gateway/config/routing.yaml`:

- code → `phi3:mini`
- story → `qwen2.5:3b`
- slogan → `gpt2-xl` (low-stakes; weak model is fine)
- translate → `qwen2.5:0.5b`

Intent wins over complexity when both could apply (`intent_priority: true`).

## Guardrails

- **Pre-call:** PII redact, prompt-injection block, blocked topics, max length
- **Post-call:** PII scrub on outputs, block obvious secret leaks

Pressure tests in `gateway/tests/test_pressure_guardrails.py` assert clean / PII / injection / blocked-topic payloads do not bypass.

## Screenshot checklist (UI)

1. Trivial → gpt2-xl (complexity tiny)
2. Hard multi-step → medium/large tier
3. Code preset → intent:code → phi3:mini
4. Story preset → intent:story → qwen2.5:3b
5. PII preset → pre_call redact event
6. Injection preset → blocked=true