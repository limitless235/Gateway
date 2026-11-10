#!/usr/bin/env bash
set -euo pipefail

echo "Pulling Ollama models for the capability ladder..."
ollama pull qwen2.5:0.5b
ollama pull qwen2.5:3b
ollama pull phi3:mini

echo "GPT-2 XL is downloaded on first request via Hugging Face (openai-community/gpt2-xl)."
echo "Done."