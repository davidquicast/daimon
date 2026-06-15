"""Provider-aware OpenAI-compatible client(s) for Daimon's models (F0/F2x).

Each modality (text, vision, omni, tts) is routed independently via
<MODALITY>_MODEL_PROVIDER in .env:

    local        -> llama.cpp / llama-server on this machine (text only)
    hf_inference -> Hugging Face Inference Providers / a ZeroGPU Space (any modality)

small-model-whisperer extends this with constrained decoding (GBNF / json-schema)
for the appraisal step in F2.

TEXT_THINKING_MODE=true switches MiniCPM5 into "thinking" mode (enable_thinking,
temp/top_p 0.9/0.95 per the model's deployment cookbook) for the main reply.
Callers that need deterministic, grammar-constrained output (e.g. F2's appraisal
step) pass enable_thinking=False explicitly to override this regardless of the
env switch - reasoning tokens would otherwise eat into a small max_tokens budget
before the grammar-constrained JSON.

Smoke test:
    python model/client.py
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

MODALITIES = ("text", "vision", "omni", "tts")

THINKING_MODE = os.environ.get("TEXT_THINKING_MODE", "false").strip().lower() in ("1", "true", "yes")


def provider_for(modality: str) -> str:
    if modality not in MODALITIES:
        raise ValueError(f"unknown modality {modality!r}, expected one of {MODALITIES}")
    return os.environ.get(f"{modality.upper()}_MODEL_PROVIDER", "local")


def get_client(modality: str = "text") -> tuple[OpenAI, str]:
    """Return (OpenAI client, model name) for `modality`, based on its provider switch."""
    provider = provider_for(modality)

    if provider == "local":
        if modality != "text":
            raise ValueError("local provider only serves the text model (MiniCPM5-1B); "
                              f"set {modality.upper()}_MODEL_PROVIDER to hf_inference")
        base_url = os.environ.get("MODEL_BASE_URL", "http://localhost:8080/v1")
        return OpenAI(base_url=base_url, api_key="sk-no-key-needed"), "local-model"

    if provider == "hf_inference":
        token = os.environ["HF_TOKEN"]
        base_url = os.environ.get("HF_INFERENCE_BASE_URL") or "https://router.huggingface.co/v1"
        model = os.environ[f"HF_{modality.upper()}_MODEL"]
        return OpenAI(base_url=base_url, api_key=token), model

    raise ValueError(f"unknown provider {provider!r} for {modality.upper()}_MODEL_PROVIDER")


def _prepare_local_kwargs(kwargs: dict, enable_thinking: bool | None) -> dict:
    """Set chat_template_kwargs.enable_thinking and matching temp/top_p defaults
    for the local llama.cpp endpoint. `enable_thinking=None` falls back to
    TEXT_THINKING_MODE; explicit True/False (e.g. appraise.py) always wins."""
    use_thinking = THINKING_MODE if enable_thinking is None else enable_thinking
    extra_body = kwargs.pop("extra_body", {})
    extra_body.setdefault("chat_template_kwargs", {}).setdefault("enable_thinking", use_thinking)
    kwargs["extra_body"] = extra_body
    if use_thinking:
        kwargs.setdefault("temperature", 0.9)
    else:
        kwargs.setdefault("temperature", 0.7)
    kwargs.setdefault("top_p", 0.95)
    return kwargs


def chat(messages, modality: str = "text", *, enable_thinking: bool | None = None, **kwargs):
    """Send a chat completion for `modality` and return the text content."""
    client, model = get_client(modality)
    if provider_for(modality) == "local":
        kwargs = _prepare_local_kwargs(kwargs, enable_thinking)
    resp = client.chat.completions.create(model=model, messages=messages, **kwargs)
    return resp.choices[0].message.content


def chat_stream(messages, modality: str = "text", *, enable_thinking: bool | None = None, **kwargs):
    """Yield (kind, text) chunks as the reply streams in.

    `kind` is "thinking" for <think> reasoning tokens (only emitted when
    enable_thinking is on and the server reports `delta.reasoning_content`)
    and "content" for the actual reply text.
    """
    client, model = get_client(modality)
    if provider_for(modality) == "local":
        kwargs = _prepare_local_kwargs(kwargs, enable_thinking)
    stream = client.chat.completions.create(model=model, messages=messages, stream=True, **kwargs)
    for chunk in stream:
        delta = chunk.choices[0].delta
        reasoning = getattr(delta, "reasoning_content", None)
        if reasoning:
            yield "thinking", reasoning
        if delta.content:
            yield "content", delta.content


if __name__ == "__main__":
    client, model = get_client("text")
    print(f"Hitting {client.base_url} (model={model}, provider={provider_for('text')}) ...")
    out = chat(
        [{"role": "user", "content": "Reply with exactly: ok"}],
        max_tokens=8,
        temperature=0.0,
    )
    print("Model replied:", repr(out))
