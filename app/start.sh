#!/usr/bin/env bash
set -euo pipefail

export MODEL_FILE="${MODEL_FILE:-MiniCPM5-1B-Q4_K_M.gguf}"
export MODEL_REPO="${MODEL_REPO:-openbmb/MiniCPM5-1B-GGUF}"
export MODEL_PATH="${MODEL_PATH:-model/weights/${MODEL_FILE}}"
export MODEL_PORT="${MODEL_PORT:-8080}"

if [ "${TEXT_MODEL_PROVIDER:-local}" = "local" ]; then
    if [ ! -f "${MODEL_PATH}" ]; then
        echo "Downloading ${MODEL_FILE} from ${MODEL_REPO} ..."
        python model/download_model.py
    fi
    bash model/serve.sh &
    echo "Waiting for model server on :${MODEL_PORT} ..."
    until curl -sf "http://localhost:${MODEL_PORT}/health" >/dev/null 2>&1; do
        sleep 2
    done
    echo "Model server ready."
fi

if [ "${UVICORN_RELOAD:-0}" = "1" ]; then
    exec uvicorn app.server:app --host 0.0.0.0 --port "${PORT:-7860}" --reload
else
    exec uvicorn app.server:app --host 0.0.0.0 --port "${PORT:-7860}"
fi
