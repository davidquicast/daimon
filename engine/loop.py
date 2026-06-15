"""F2 living loop: orchestrates one chat turn through all six steps.

    1. RESPONSE     - MiniCPM5-1B replies as Daimon, using PERSONA.md itself
                       (engine/recompile.py, re-rendered from personaxis.md +
                       state.json before every turn) as the system prompt -
                       this IS Daimon's self-improving prompt - plus the
                       conversation history the caller passes in (the UI's
                       own `gr.Chatbot` history; see build_messages()).
    2. APPRAISAL    - engine/appraise.py: small GBNF-constrained JSON signals.
    3. MAPPING      - engine/mapping.py: deterministic signals -> deltas.
    4. GOVERN+CLAMP - engine/spec_bridge.py: `mutate()` per delta (clamp +
                       envelope check + audit log live in the spec engine,
                       not here).
    5. RECOMPILE    - engine/recompile.py: re-render PERSONA.md from the
                       updated state.json.
    6. MEMORY       - engine/memory.py: let the model curate memory.md and
                       memory/<date>.md (cross-session long-term memory +
                       this session's consolidated summary) - two extra
                       small local-model calls are cheap, so they run every
                       turn.

The model never writes state.json directly - every mutation goes through
spec_bridge.mutate(), which reads personaxis.md's declared envelopes and
applies clamping and the audit log entirely in Python.

Run the Gate G2 smoke test (5 turns) with:

    python -m engine.loop

Requires `bash model/serve.sh` (MiniCPM5-1B on http://localhost:8080/v1) to be
running first - see MASTER_CHECKLIST F0.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from engine import mapping, memory, recompile  # noqa: E402
from engine.appraise import appraise  # noqa: E402
from engine.spec_bridge import SpecBridgeError, get_state, mutate  # noqa: E402
from model.client import THINKING_MODE, chat, chat_stream  # noqa: E402

SLUG = "daimon"

# In thinking mode, the <think> block itself can run past 1000 tokens with
# Daimon's full system prompt before any reply content is produced - give it
# plenty of room (CTX=32768), and ask the model to keep that reasoning short
# (see build_messages) so it doesn't eat the whole budget before replying.
DEFAULT_MAX_TOKENS = 4096 if THINKING_MODE else 300

_THINKING_BUDGET_NOTE = (
    "\n\n## Reasoning budget\n\nBefore replying, think briefly - a short "
    "paragraph, not an essay - then give your reply. Always leave room for "
    "the reply itself; an unfinished reply is worse than a short one."
)

# How many prior chat turns (user+assistant pairs) to replay for multi-turn
# coherence. The conversation itself lives only in the caller's gr.Chatbot
# history - nothing is persisted to disk.
MAX_HISTORY_TURNS = 8


def build_messages(user_message: str, history: list[dict[str, Any]] | None = None) -> list[dict[str, str]]:
    # PERSONA.md *is* the system prompt: Identity, Character, Personality &
    # Voice, Values, Limits, Self-Improvement, plus the live "Current State"
    # section, all re-rendered from personaxis.md + state.json every turn.
    system_prompt = recompile.render(SLUG)
    if THINKING_MODE:
        system_prompt += _THINKING_BUDGET_NOTE

    messages = [{"role": "system", "content": system_prompt}]
    for turn in (history or [])[-MAX_HISTORY_TURNS * 2 :]:
        role, content = turn.get("role"), turn.get("content")
        # Skip collapsible "thinking" bubbles (gr.Chatbot metadata) - only
        # replay the visible user/assistant text.
        if role in ("user", "assistant") and isinstance(content, str) and content and not turn.get("metadata"):
            messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": user_message})
    return messages


def finish_turn(user_message: str, reply: str) -> dict[str, Any]:
    """Steps 2-6: appraise the (user_message, reply) pair, map signals to
    deltas, apply clamped+audited mutations, recompile PERSONA.md, and let
    the model curate its long-term memory. Used by both step() (non-streaming)
    and the UI/API, after the reply has finished streaming."""
    signals = appraise(user_message, reply)
    deltas = mapping.signals_to_deltas(signals)

    applied: list[dict[str, Any]] = []
    for field, delta, reason in deltas:
        try:
            applied.append(mutate(SLUG, field, delta, reason=reason, actor="actor-llm"))
        except SpecBridgeError as exc:
            applied.append({"field": field, "delta": delta, "blocked": True, "error": str(exc)})

    persona_live_path = recompile.write(SLUG)
    memory.curate_memory(SLUG, user_message, reply)

    return {
        "reply": reply,
        "signals": signals,
        "mutations": applied,
        "persona_live_path": str(persona_live_path),
        "state": get_state(SLUG),
    }


def step(user_message: str, history: list[dict[str, Any]] | None = None, *, max_tokens: int = DEFAULT_MAX_TOKENS) -> dict[str, Any]:
    """Run one full living-loop turn. Returns the reply, appraisal signals,
    mutations actually applied (clamped/blocked included), the path to the
    re-rendered PERSONA.md, and the resulting state."""
    messages = build_messages(user_message, history)
    reply = chat(messages, modality="text", max_tokens=max_tokens)
    return finish_turn(user_message, reply)


def step_stream(user_message: str, history: list[dict[str, Any]] | None = None, *, max_tokens: int = DEFAULT_MAX_TOKENS):
    """Generator: yields ("thinking" | "content", text) chunks as the reply
    streams in, then a final ("done", reply) tuple with the full reply text.
    Does NOT run steps 2-6 - callers run finish_turn(user_message, reply)
    themselves once they're ready (e.g. after unblocking the chat UI)."""
    messages = build_messages(user_message, history)
    parts: list[str] = []
    for kind, text in chat_stream(messages, modality="text", max_tokens=max_tokens):
        if kind == "content":
            parts.append(text)
        yield kind, text
    yield "done", "".join(parts)


# Gate G2 smoke test: 5 turns that should each nudge the vector and leave an
# audit trail, without runaway (deltas are capped, see engine/mapping.py).
_DEMO_TURNS = [
    "Hey Daimon! I love how curious you are, tell me something interesting.",
    "Whoa, that's such a cool fact, can you go deeper on that?",
    "Actually, can you be a bit more reserved and less chatty for a moment?",
    "Sorry if that came across harsh, I just need to focus for a bit.",
    "No worries! I'm back, let's keep exploring - what else have you got?",
]


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")

    # Stand in for gr.Chatbot's session history: each turn appends its own
    # (user, reply) pair so the next turn keeps multi-turn context, just
    # like the UI does - nothing is persisted to disk.
    history: list[dict[str, Any]] = []
    for i, turn in enumerate(_DEMO_TURNS, start=1):
        print(f"\n=== Turn {i}: {turn!r} ===")
        result = step(turn, history)
        print("reply:", result["reply"])
        print("signals:", result["signals"])
        print("mutations:", result["mutations"])
        history.append({"role": "user", "content": turn})
        history.append({"role": "assistant", "content": result["reply"]})
