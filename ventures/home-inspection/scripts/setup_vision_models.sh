#!/usr/bin/env bash
# Operator-initiated, local-only installation and acceptance. Does not open the network.
# Only the explicit `ollama pull` phase downloads public model weights.
set -euo pipefail
WRITER="${1:-qwen2.5vl:3b}"
REVIEWER="${2:-granite3.2-vision:2b}"
if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3.12+ must be installed first." >&2; exit 2
fi
if ! command -v ollama >/dev/null 2>&1; then
  echo "Install official Ollama from https://ollama.com/download and rerun. No new account required." >&2; exit 2
fi
mkdir -p local-results
PROOF_DIR="local-results/activation-$(date +%Y%m%d-%H%M%S)-$$"
if python3 -m scripts.activate_vision --out-dir "$PROOF_DIR" \
  --writer-model "$WRITER" --review-model "$REVIEWER" \
  --start-server --download-models --run-live-gate; then
  echo "Activation record: $PROOF_DIR/activation_status.json"
else
  status=$?
  echo "Activation blocked: $PROOF_DIR/activation_status.json" >&2
  exit "$status"
fi
