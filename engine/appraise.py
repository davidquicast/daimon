"""Step 2 of the living loop: appraisal (F2).

Calls the text model (MiniCPM5-1B via model/client.py) with a small GBNF
grammar (engine/grammars/appraisal.gbnf) that guarantees a valid, minimal
JSON object describing how the last exchange should nudge Daimon's state
vector. The model PROPOSES signals; engine/mapping.py and
engine/spec_bridge.py turn them into clamped, audited mutations - the model
never writes state.json directly.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from model.client import chat  # noqa: E402

GRAMMAR_PATH = Path(__file__).resolve().parent / "grammars" / "appraisal.gbnf"
_GRAMMAR = GRAMMAR_PATH.read_text(encoding="utf-8")

_SYSTEM_PROMPT = (
    "You are an appraisal module for a persona named Daimon. Given the user's "
    "last message and Daimon's reply, output ONLY a JSON object describing how "
    "the exchange should nudge Daimon's internal state. Fields:\n"
    "- sentiment: overall tone of the user's message, from -1.0 (hostile/negative) "
    "to 1.0 (warm/positive), in steps of 0.5.\n"
    "- engagement: how exploratory/engaged the exchange is, 0.0 (flat/closing) to "
    "1.0 (curious/exploratory), in steps of 0.25.\n"
    "- correction: true if the user explicitly asked Daimon to change how it acts "
    "(its tone, talkativeness, openness, or agreeableness), false otherwise.\n"
    "- target: which trait the correction is about - one of tone, openness, "
    "extraversion, agreeableness, none.\n"
    "- direction: -1 if the user wants less of that trait, 1 if more, 0 if there "
    "is no correction.\n"
    "- reason: a short (under 12 words) plain-text reason for this reading.\n"
)

_NEUTRAL: dict = {
    "sentiment": 0.0,
    "engagement": 0.0,
    "correction": False,
    "target": "none",
    "direction": 0,
    "reason": "appraisal output unparsable, defaulting to neutral",
}

_VALID_TARGETS = {"tone", "openness", "extraversion", "agreeableness", "none"}


def appraise(user_message: str, persona_reply: str, *, max_tokens: int = 200) -> dict:
    """Return a validated appraisal dict, falling back to a neutral reading if
    the model's output cannot be parsed."""
    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"User said: {user_message!r}\nDaimon replied: {persona_reply!r}\n"
                "Output the JSON object now."
            ),
        },
    ]
    raw = chat(
        messages,
        modality="text",
        max_tokens=max_tokens,
        temperature=0.1,
        enable_thinking=False,  # grammar-constrained JSON; reasoning tokens would eat max_tokens
        extra_body={"grammar": _GRAMMAR},
    )
    return _parse(raw)


def _parse(raw: str) -> dict:
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return dict(_NEUTRAL)

    out = dict(_NEUTRAL)
    if isinstance(data.get("sentiment"), (int, float)):
        out["sentiment"] = max(-1.0, min(1.0, float(data["sentiment"])))
    if isinstance(data.get("engagement"), (int, float)):
        out["engagement"] = max(0.0, min(1.0, float(data["engagement"])))
    if isinstance(data.get("correction"), bool):
        out["correction"] = data["correction"]
    if data.get("target") in _VALID_TARGETS:
        out["target"] = data["target"]
    if data.get("direction") in (-1, 0, 1):
        out["direction"] = data["direction"]
    if isinstance(data.get("reason"), str) and data["reason"].strip():
        out["reason"] = data["reason"].strip()[:120]
    return out


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    result = appraise(
        "Wow, that's such a cool way to put it, tell me more!",
        "Glad you liked that! There's a lot more to explore here...",
    )
    print(result)
