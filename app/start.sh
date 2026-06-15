#!/usr/bin/env bash
# Space entrypoint (F4/F6): bring up the local model server, then the app.
# Replaces the F0 placeholder `bash model/serve.sh` as the Dockerfile CMD.
set -euo pipefail

MODEL_FILE="${MODEL_FILE:-}"
MODEL_PATH="${MODEL_PATH:-model/weights/${MODEL_FILE}}"

if [ "${TEXT_MODEL_PROVIDER:-local}" = "local" ]; then
  if [ -n "${MODEL_FILE}" ] && [ ! -f "${MODEL_PATH}" ]; then
    python model/download_model.py
  fi
  bash model/serve.sh &
fi

# UVICORN_RELOAD=1 (local dev, e.g. `docker run -v $(pwd):/app`) hot-reloads on
# code edits. Unset/0 for the HF Space (F6).
if [ "${UVICORN_RELOAD:-0}" = "1" ]; then
  exec uvicorn app.server:app --host 0.0.0.0 --port "${PORT:-7860}" --reload
else
  exec uvicorn app.server:app --host 0.0.0.0 --port "${PORT:-7860}"
fi
