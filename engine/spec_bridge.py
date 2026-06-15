"""Pure-Python spec engine for personaxis.md personas (F1).

The living loop (F2) must never write state.json directly. Every mutation
goes through `mutate()` here: it reads the declared envelope (range) for a
field straight from <slug>/personaxis.md, clamps the requested delta to that
envelope, appends an audit-log entry, and writes <slug>/state.json. There is
no external CLI or subprocess involved - personaxis.md (the spec) and
state.json (the runtime values) are just YAML/JSON files this module reads
and writes directly.

Usage:
    from engine.spec_bridge import mutate, validate, get_state

    result = mutate("daimon", "mood.tone", 0.05, reason="user seemed pleased")
    state = get_state("daimon")
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
PERSONAS_DIR = REPO_ROOT / ".personaxis" / "personas"

Actor = Literal[
    "actor-llm",
    "runtime-decay",
    "runtime-context",
    "human-operator",
    "judge-correction",
]

# field prefix -> path of dict keys to reach {mean, range} in personaxis.md
_ENVELOPE_PATH: dict[str, tuple[str, ...]] = {
    "traits": ("personality", "traits"),
    "affect": ("affect", "baseline", "core_affect"),
    "mood": ("affect", "baseline", "mood"),
}


class SpecBridgeError(RuntimeError):
    """Raised when a mutation targets a field with no declared envelope, or
    when personaxis.md / state.json cannot be found or parsed."""


def _persona_md_path(slug: str) -> Path:
    path = PERSONAS_DIR / slug / "personaxis.md"
    if not path.exists():
        raise SpecBridgeError(f"No personaxis.md for persona '{slug}' at {path}")
    return path


def _state_path(slug: str) -> Path:
    path = PERSONAS_DIR / slug / "state.json"
    if not path.exists():
        raise SpecBridgeError(f"No state.json for persona '{slug}' at {path}")
    return path


def _load_spec(slug: str) -> dict[str, Any]:
    text = _persona_md_path(slug).read_text(encoding="utf-8")
    _, frontmatter, _ = text.split("---", 2)
    return yaml.safe_load(frontmatter)


def _envelope(spec: dict[str, Any], field: str) -> tuple[float, float] | None:
    """Return the declared (lo, hi) range for `field` (e.g. "mood.tone"), or
    None if `field` has no envelope in personaxis.md (personality/affect
    layers only - identity, character, etc. are not reachable here)."""
    layer, _, name = field.partition(".")
    path = _ENVELOPE_PATH.get(layer)
    if path is None:
        return None
    node: Any = spec
    for key in path:
        node = node.get(key, {})
    spec_field = node.get(name)
    if not spec_field or "range" not in spec_field:
        return None
    lo, hi = spec_field["range"]
    return float(lo), float(hi)


def mutate(
    slug: str,
    field: str,
    delta: float,
    *,
    reason: str,
    actor: Actor = "actor-llm",
) -> dict[str, Any]:
    """Apply a clamped, audited mutation to <slug>/state.json.

    Returns {"field", "from", "to", "clamped", "blocked", "raw"}.
    Raises SpecBridgeError if `field` has no declared envelope in
    personaxis.md (structural rejection - e.g. identity.*, character.*).
    """
    spec = _load_spec(slug)
    envelope = _envelope(spec, field)
    if envelope is None:
        raise SpecBridgeError(
            f"No envelope declared for '{field}' in {slug}'s personaxis.md "
            "(only personality.traits.*, affect.baseline.core_affect.* and "
            "affect.baseline.mood.* are mutable) - mutation refused."
        )
    lo, hi = envelope

    state_path = _state_path(slug)
    state = json.loads(state_path.read_text(encoding="utf-8"))
    if field not in state["values"]:
        raise SpecBridgeError(f"'{field}' has a declared envelope but no entry in {slug}'s state.json values.")

    before = float(state["values"][field])
    requested = before + delta
    after = min(max(requested, lo), hi)
    clamped = abs(after - requested) > 1e-12

    state["values"][field] = after
    state["mutation_log"].append(
        {
            "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.") + f"{datetime.now(timezone.utc).microsecond // 1000:03d}Z",
            "field": field,
            "from": before,
            "to": after,
            "delta_requested": delta,
            "clamped": clamped,
            "reason": reason,
            "actor": actor,
            "governance_blocked": False,
        }
    )
    state_path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")

    raw = f"ok {field}: {before} -> {after}"
    if clamped:
        raw += f" (clamped to [{lo}, {hi}])"
    return {"field": field, "from": before, "to": after, "clamped": clamped, "blocked": False, "raw": raw}


def validate(slug: str) -> dict[str, Any]:
    """Check that every value in <slug>/state.json sits within its declared
    envelope. Returns {"ok", "status", "raw"}."""
    spec = _load_spec(slug)
    state = get_state(slug)
    violations = []
    for field, value in state["values"].items():
        envelope = _envelope(spec, field)
        if envelope is None:
            continue
        lo, hi = envelope
        if not (lo - 1e-9 <= value <= hi + 1e-9):
            violations.append(f"{field}={value} outside [{lo}, {hi}]")

    if violations:
        return {"ok": False, "status": "FAIL", "raw": "FAIL: " + "; ".join(violations)}
    return {"ok": True, "status": "PASS", "raw": "PASS: all values within declared envelopes"}


def get_state(slug: str) -> dict[str, Any]:
    """Read the current <slug>/state.json (values, mutation_log, etc.)."""
    return json.loads(_state_path(slug).read_text(encoding="utf-8"))


if __name__ == "__main__":
    import sys

    sys.stdout.reconfigure(encoding="utf-8")

    # Smoke test for Gate G1: a clamped mutation + audit log entry, end-to-end from Python.
    slug = "daimon"
    print(f"validate({slug}) ->", validate(slug))

    before = get_state(slug)["values"]["mood.tone"]
    print(f"mood.tone before: {before}")

    result = mutate(
        slug,
        "mood.tone",
        1.0,
        reason="smoke test: large positive delta should clamp to range max",
        actor="actor-llm",
    )
    print("mutate ->", result)

    after = get_state(slug)
    print(f"mood.tone after: {after['values']['mood.tone']}")
    print(f"mutation_log entries: {len(after['mutation_log'])}")
    print(f"last entry: {after['mutation_log'][-1]}")
