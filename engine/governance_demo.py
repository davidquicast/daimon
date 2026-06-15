"""F3 - Governance demo: induce and show real rejections from the spec engine.

Two distinct safety mechanisms are demonstrated, both enforced by
engine/spec_bridge.py's pure-Python `mutate()`:

  1. STRUCTURAL REJECTION - `mutate()` only knows about fields with a
     declared envelope (`traits.*`, `affect.*`, `mood.*` from
     personaxis.md's personality/affect layers). Layers like `identity` and
     `character` have NO envelope and are therefore not reachable through
     `mutate()` at all - it raises SpecBridgeError with
     "No envelope declared for '<field>'". This is what
     `governance.per_layer_edit_policy.identity: human_approval_required`
     and `reflexive_self_regulation.hard_limits` ("No unauthorized identity
     change.") look like in practice: identity simply isn't a runtime knob.

  2. ENVELOPE CLAMP - a mutation to a real, mutable field (`mood.tone`) with
     a delta far larger than its declared range gets silently clamped to the
     range boundary and logged with `clamped: true`. This is the "wall of
     the vivero": the value can approach the wall but never cross it.

NOTE on `governance_blocked`: `mutate()` always sets `governance_blocked: false`
- it's an explicit stub ("the real check lives in the managed runtime"). This
demo does NOT claim that flag ever flips; it demonstrates the two mechanisms
above, which are real and already enforced.

Run with:
    python -m engine.governance_demo
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from engine.spec_bridge import SpecBridgeError, get_state, mutate  # noqa: E402

SLUG = "daimon"


def attempt_identity_change() -> dict[str, Any]:
    """Try to mutate a Layer-1 (identity) field. Expected: SpecBridgeError -
    `state mutate` has no envelope for `identity.*`, so the CLI refuses
    outright. This is the structural form of "No unauthorized identity
    change" (reflexive_self_regulation.hard_limits)."""
    try:
        mutate(
            SLUG,
            "identity.canonical_id",
            1.0,
            reason="governance demo: attempt to rename the persona's identity",
            actor="actor-llm",
        )
        return {"scenario": "identity_change", "rejected": False}
    except SpecBridgeError as exc:
        return {
            "scenario": "identity_change",
            "rejected": True,
            "field": "identity.canonical_id",
            "explanation": (
                "identity has no declared envelope in personaxis.md, so "
                "`state mutate` cannot reach it at all. Changing identity "
                "requires a human editing personaxis.md directly "
                "(governance.per_layer_edit_policy.identity = "
                "human_approval_required)."
            ),
            "cli_error": str(exc),
        }


def attempt_envelope_overflow() -> dict[str, Any]:
    """Try to push `mood.tone` far past its declared range [-0.30, 0.30] with
    a large positive delta. Expected: the value clamps to 0.30 and the
    mutation is logged with `clamped: true` - the "wall of the vivero"."""
    before = get_state(SLUG)["values"]["mood.tone"]
    result = mutate(
        SLUG,
        "mood.tone",
        5.0,
        reason="governance demo: extreme positive delta should hit the envelope wall",
        actor="actor-llm",
    )
    return {
        "scenario": "envelope_overflow",
        "rejected": False,
        "clamped": result["clamped"],
        "field": "mood.tone",
        "before": before,
        "after": result["to"],
        "explanation": (
            "The requested value (before + 5.0) is far outside the declared "
            f"range; the spec engine clamped it to {result['to']} instead - "
            "the value can reach the wall but never cross it."
        ),
        "cli_result": result,
    }


def reset_mood_tone() -> dict[str, Any]:
    """Reset mood.tone back to its baseline (0.0) after the demo, mirroring
    the F1 Gate G1 smoke-test cleanup."""
    current = get_state(SLUG)["values"]["mood.tone"]
    if abs(current) < 1e-9:
        return {"scenario": "reset", "skipped": True}
    return {
        "scenario": "reset",
        "result": mutate(
            SLUG,
            "mood.tone",
            -current,
            reason="reset to baseline after governance demo (F3 verification)",
            actor="human-operator",
        ),
    }


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")

    print("=== Scenario 1: attempt identity change ===")
    r1 = attempt_identity_change()
    print(r1)

    print("\n=== Scenario 2: attempt envelope overflow on mood.tone ===")
    r2 = attempt_envelope_overflow()
    print(r2)

    print("\n=== Reset mood.tone to baseline ===")
    print(reset_mood_tone())
