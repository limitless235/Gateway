# Local AI Gateway

A LiteLLM-inspired **local AI gateway** with:

- OpenAI-compatible `POST /v1/chat/completions`
- **Capability-tier routing** (weakest → strongest): `gpt2-xl` → `qwen2.5:0.5b` → `qwen2.5:3b` → `phi3:mini`
- **Intent specialty routing** (code → Phi, story → Qwen 3B, slogan → GPT-2 XL)
- **Pre-call / post-call guardrails** (PII redaction, injection/topic blocks, secret-leak scrub)
- React demo UI for screenshots and live traces

Article/blog publishing is deferred; see [`docs/litellm-notes.md`](docs/litellm-notes.md).

## Prerequisites

- macOS Apple Silicon (tested target: M4 Air 16GB)
- [Ollama](https://ollama.com) running locally
- Python 3.12 or 3.13 (3.14 may lack wheels for torch/transformers) and Node 20+
- [`uv`](https://github.com/astral-sh/uv) recommended for the venv

## Setup

```bash
# Models
./scripts/pull_models.sh

# Gateway (Python 3.13)
cd gateway
uv venv --python 3.13 .venv
source .venv/bin/activate
uv pip install -r requirements.txt

# UI
cd ../ui
npm install
```

## Run

Terminal 1 — gateway:

```bash
./scripts/run_gateway.sh
```

Terminal 2 — UI:

```bash
cd ui && npm run dev
```

Open http://localhost:5173 — chat presets on the left, routing/guardrail trace on the right.

API docs: http://127.0.0.1:8000/docs

## Demo script

With the gateway up:

```bash
python3 scripts/demo_routing.py
```

## Tests

```bash
cd gateway
source .venv/bin/activate
PYTHONPATH=. pytest -q
```

## Config

- [`gateway/config/models.yaml`](gateway/config/models.yaml) — model registry + tiers
- [`gateway/config/routing.yaml`](gateway/config/routing.yaml) — intent pins + complexity thresholds

## Note on GPT-2 XL

`gpt2-xl` is the **largest official GPT-2** and the **weakest** model in this ladder. Param count ≠ intelligence — Phi-3 mini is the strongest local tier here. GPT-2 downloads from Hugging Face on first use.