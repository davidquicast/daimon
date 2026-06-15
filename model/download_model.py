"""Download the local text model GGUF into model/weights/ (TEXT_MODEL_PROVIDER=local only).

Defaults to MiniCPM5-1B (Tiny Titan, <=4B). Override MODEL_REPO/MODEL_FILE in .env to
pin a different GGUF/quant.

Usage:
    python model/download_model.py
"""

import os
import sys
from pathlib import Path

WEIGHTS_DIR = Path(__file__).resolve().parent / "weights"

DEFAULT_REPO = "openbmb/MiniCPM5-1B-GGUF"
DEFAULT_FILE = "MiniCPM5-1B-Q4_K_M.gguf"


def main() -> int:
    repo = os.environ.get("MODEL_REPO", "").strip() or DEFAULT_REPO
    filename = os.environ.get("MODEL_FILE", "").strip() or DEFAULT_FILE

    if repo == DEFAULT_REPO and filename == DEFAULT_FILE:
        print(f"Using default text model: {repo}/{filename} (override via MODEL_REPO/MODEL_FILE in .env)")

    try:
        from huggingface_hub import hf_hub_download
    except ImportError:
        print("huggingface-hub is not installed. Run: pip install -r requirements.txt", file=sys.stderr)
        return 1

    WEIGHTS_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Downloading {filename} from {repo} ...")
    path = hf_hub_download(repo_id=repo, filename=filename, local_dir=str(WEIGHTS_DIR))
    print(f"Model ready at: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
