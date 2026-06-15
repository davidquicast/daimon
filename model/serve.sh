#!/usr/bin/env bash
# Serve the local text model (MiniCPM5-1B) as an OpenAI-compatible endpoint (F0).
# Only used when TEXT_MODEL_PROVIDER=local (see .env.example).
set -euo pipefail

PORT="${MODEL_PORT:-8080}"
CTX="${CTX:-8192}"
MODEL_FILE="${MODEL_FILE:-}"
MODEL_PATH="${MODEL_PATH:-model/weights/${MODEL_FILE}}"

# HARDWARE=auto detects a CUDA GPU via nvidia-smi and offloads all layers (NGL=99);
# otherwise runs CPU-only (NGL=0). Set HARDWARE=gpu or HARDWARE=cpu to force,
# or set NGL directly to override both.
HARDWARE="${HARDWARE:-auto}"
if [ -n "${NGL:-}" ]; then
  : # NGL explicitly set, respect it
elif [ "${HARDWARE}" = "cpu" ]; then
  NGL=0
elif [ "${HARDWARE}" = "gpu" ]; then
  NGL=99
elif command -v nvidia-smi >/dev/null 2>&1 && nvidia-smi >/dev/null 2>&1; then
  NGL=99
else
  NGL=0
fi
echo "Hardware: ${HARDWARE} -> NGL=${NGL}"

if [ -z "${MODEL_FILE}" ] || [ ! -f "${MODEL_PATH}" ]; then
  echo "Model not found at '${MODEL_PATH}'." >&2
  echo "Set MODEL_FILE (and run model/download_model.py) once the checkpoint is pinned." >&2
  exit 1
fi

# llama-server (llama.cpp C++ binary, built in the Dockerfile) exposes an
# OpenAI-compatible API at /v1. --jinja applies MiniCPM5's chat template.
if ! command -v llama-server >/dev/null 2>&1; then
  echo "llama-server not found on PATH. Build it from https://github.com/ggml-org/llama.cpp" >&2
  exit 1
fi
exec llama-server -m "${MODEL_PATH}" --host 0.0.0.0 --port "${PORT}" -c "${CTX}" -ngl "${NGL}" --jinja
