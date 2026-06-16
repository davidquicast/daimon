#!/usr/bin/env bash
set -euo pipefail

export TEXT_MODEL_PROVIDER="${TEXT_MODEL_PROVIDER:-local}"
export VISION_MODEL_PROVIDER="${VISION_MODEL_PROVIDER:-hf_inference}"
export OMNI_MODEL_PROVIDER="${OMNI_MODEL_PROVIDER:-hf_inference}"
export TTS_MODEL_PROVIDER="${TTS_MODEL_PROVIDER:-hf_inference}"

export HARDWARE="${HARDWARE:-auto}"
export MODEL_REPO="${MODEL_REPO:-openbmb/MiniCPM5-1B-GGUF}"
export MODEL_FILE="${MODEL_FILE:-MiniCPM5-1B-Q4_K_M.gguf}"
export MODEL_PORT="${MODEL_PORT:-8080}"
export MODEL_PATH="${MODEL_PATH:-model/weights/${MODEL_FILE}}"
export MODEL_BASE_URL="${MODEL_BASE_URL:-http://localhost:${MODEL_PORT}/v1}"
export CTX="${CTX:-32768}"

export HF_TEXT_MODEL="${HF_TEXT_MODEL:-openbmb/MiniCPM5-1B}"
export HF_VISION_MODEL="${HF_VISION_MODEL:-openbmb/MiniCPM-V-4.6}"
export HF_OMNI_MODEL="${HF_OMNI_MODEL:-openbmb/MiniCPM-o-4_5}"
export HF_TTS_MODEL="${HF_TTS_MODEL:-openbmb/VoxCPM2}"

if [ "${TEXT_MODEL_PROVIDER}" = "local" ]; then
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
