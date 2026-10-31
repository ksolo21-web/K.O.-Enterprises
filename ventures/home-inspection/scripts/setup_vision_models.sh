#!/usr/bin/env bash
# No additional accounts, no paid service. This downloads public model weights
# ONLY when a user explicitly runs it on a computer with network access.
set -euo pipefail
WRITER="${1:-qwen2.5vl:3b}"
REVIEWER="${2:-granite3.2-vision:2b}"
if [[ "${OLLAMA_HOST:-127.0.0.1:11434}" != "127.0.0.1:11434" && "${OLLAMA_HOST:-}" != "http://127.0.0.1:11434" ]]; then
  echo 'STOP: Configure OLLAMA_HOST=127.0.0.1:11434 (loopback only).' >&2; exit 2
fi
if ! command -v ollama >/dev/null 2>&1; then
  echo 'Install official Ollama from https://ollama.com/download or https://ollama.com/download/linux then rerun.' >&2
  exit 2
fi
if ! python3 -c 'import PIL' >/dev/null 2>&1; then
  echo 'Install Python dependencies from the project requirements.txt before running this script.' >&2; exit 2
fi
if ! python3 -m inspection_engine model-preflight --writer-model "$WRITER" --review-model "$REVIEWER" >/dev/null 2>&1; then
  echo "Pulling writer model $WRITER (network download, no account required)"
  ollama pull "$WRITER"
  echo "Pulling reviewer model $REVIEWER (network download, no account required)"
  ollama pull "$REVIEWER"
fi
python3 -m inspection_engine model-preflight --writer-model "$WRITER" --review-model "$REVIEWER"
mkdir -p local-results
python3 -m inspection_engine model-smoke --writer-model "$WRITER" --review-model "$REVIEWER" --out "local-results/vision-smoke-$(date +%Y%m%d-%H%M%S).json"
echo 'Synthetic image-conditioned model check completed; real inspection accuracy still unverified.'
