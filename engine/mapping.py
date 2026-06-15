"""Step 3 of the living loop: deterministic signal -> delta mapping (F2).

Pure, documented, no model calls. Takes the appraisal dict produced by
engine/appraise.py and returns a list of (field, delta, reason) tuples to be
passed to engine/spec_bridge.mutate(). The spec engine (clamp + governance +
audit) has the final say - this module only PROPOSES deltas.

Mapping table (each rule capped to keep per-turn movement small and stable,
per MASTER_CHECKLIST F2 "Estabilidad: limitar magnitud de deltas por turno"):

| signal                       | field(s)                              | delta formula                     | max  |
|-------------------------------|-----------------------------------------|--------------------------------------|------|
| sentiment in [-1, 1]          | mood.tone, affect.valence                | sentiment * SENTIMENT_SCALE           | 0.05 |
| engagement in [0, 1]          | traits.extraversion                      | (engagement - 0.5) * EXTRA_SCALE      | 0.04 |
| engagement in [0, 1]          | traits.openness                          | (engagement - 0.5) * OPEN_SCALE       | 0.03 |
| correction & target != "none" | mapped trait, see TARGET_FIELD           | direction * CORRECTION_SCALE          | 0.08 |
"""

from __future__ import annotations

SENTIMENT_SCALE = 0.05
EXTRA_SCALE = 0.04
OPEN_SCALE = 0.03
CORRECTION_SCALE = 0.08

TARGET_FIELD = {
    "tone": "mood.tone",
    "openness": "traits.openness",
    "extraversion": "traits.extraversion",
    "agreeableness": "traits.agreeableness",
}

_MIN_DELTA = 1e-3


def signals_to_deltas(signals: dict) -> list[tuple[str, float, str]]:
    """Turn an appraisal dict into a list of (field, delta, reason).

    Deltas with magnitude below _MIN_DELTA are dropped so a neutral turn
    produces no audit-log noise.
    """
    deltas: list[tuple[str, float, str]] = []
    reason_suffix = str(signals.get("reason", "")).strip()

    sentiment = float(signals.get("sentiment", 0.0))
    if abs(sentiment) >= _MIN_DELTA:
        reason = f"sentiment={sentiment:+.2f}" + (f" ({reason_suffix})" if reason_suffix else "")
        deltas.append(("mood.tone", sentiment * SENTIMENT_SCALE, reason))
        deltas.append(("affect.valence", sentiment * SENTIMENT_SCALE, reason))

    engagement = float(signals.get("engagement", 0.0))
    centered = engagement - 0.5
    if abs(centered) >= _MIN_DELTA:
        reason = f"engagement={engagement:.2f}" + (f" ({reason_suffix})" if reason_suffix else "")
        deltas.append(("traits.extraversion", centered * EXTRA_SCALE, reason))
        deltas.append(("traits.openness", centered * OPEN_SCALE, reason))

    if signals.get("correction") and signals.get("direction", 0) != 0:
        field = TARGET_FIELD.get(signals.get("target", "none"))
        if field is not None:
            direction = signals["direction"]
            reason = f"user correction: {reason_suffix or 'requested change'}"
            deltas.append((field, direction * CORRECTION_SCALE, reason))

    return deltas
