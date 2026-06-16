"""Step 5 of the living loop: live PERSONA.md recompile (F2).

The full `personaxis compile` (cli/src/compile-instructions.ts) is an LLM-based
translation of personaxis.md (10-layer quantitative spec) into the prose
structure documented in `cli/templates/PERSONA_template.md` - too heavy to
re-run every chat turn. This module instead does a CHEAP, DETERMINISTIC,
no-LLM recompile that follows the SAME section contract (Identity & Purpose,
Character, Personality & Voice, Values, How You Think, Limits,
Self-Improvement, Resources) - no invented top-level sections. The live
state.json snapshot (current trait/affect/mood values + mutation_log) is
rendered as subsections of Self-Improvement, showing where Daimon stands
right now relative to its declared baselines.

Written to `.personaxis/<slug>/PERSONA.md` after every turn - this is THE
self-improving document the UI streams: the same persona description, updated
in place as the chat history nudges Daimon's personality/affect/mood within
the envelopes declared in personaxis.md.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import yaml  # noqa: E402

from engine.spec_bridge import PERSONAS_DIR, _persona_md_path, get_state  # noqa: E402


def _load_spec(slug: str) -> dict:
    text = _persona_md_path(slug).read_text(encoding="utf-8")
    _, frontmatter, _ = text.split("---", 2)
    return yaml.safe_load(frontmatter)


def _load_policy(slug: str) -> dict:
    path = PERSONAS_DIR / slug / "policy.yaml"
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _relative_word(value: float, mean: float, range_: list[float]) -> str:
    """Qualitative position of `value` relative to its baseline `mean`,
    scaled by the declared range - never surfaces the raw numbers
    themselves (PERSONA.md must stay free of personaxis.md's quantitative
    values, per the spec's qualitative-compilation rule)."""
    span = max(range_[1] - range_[0], 1e-6)
    rel = (value - mean) / span
    if rel > 0.15:
        return "well above"
    if rel > 0.04:
        return "a bit above"
    if rel < -0.15:
        return "well below"
    if rel < -0.04:
        return "a bit below"
    return "at"


def _describe_trait(name: str, value: float, spec_trait: dict) -> str:
    word = _relative_word(value, spec_trait["mean"], spec_trait["range"])
    expression = spec_trait.get("expression", "")
    gist = expression.split(";")[0].split(".")[0].strip().rstrip(".")
    label = name.replace("_", " ")
    if word == "at":
        position = f"{label} is sitting at its usual baseline"
    else:
        position = f"{label} is currently running {word} its usual baseline"
    if gist:
        return f"{position} ({gist.lower()})."
    return f"{position}."


def _describe_dimension(label: str, value: float, spec_dim: dict) -> str:
    word = _relative_word(value, spec_dim["mean"], spec_dim["range"])
    if word == "at":
        return f"{label} is sitting at its usual baseline."
    return f"{label} is currently running {word} its usual baseline."


def _describe_mutation(entry: dict, field_ranges: dict[str, list[float]]) -> str:
    field, before, after = entry["field"], entry["from"], entry["to"]
    delta = after - before
    range_ = field_ranges.get(field)
    span = max(range_[1] - range_[0], 1e-6) if range_ else 1.0
    rel = abs(delta) / span
    if abs(delta) < 1e-9:
        size = "held steady"
    else:
        direction = "nudged up" if delta > 0 else "nudged down"
        magnitude = "slightly" if rel < 0.02 else "moderately" if rel < 0.08 else "noticeably"
        size = f"{direction} {magnitude}"
    tags = ""
    if entry.get("clamped"):
        tags += " (hit the envelope wall)"
    if entry.get("governance_blocked"):
        tags += " [BLOCKED]"
    return f"- `{field}` {size}{tags} - {entry['reason']}"


_LAYER_DEFS = [
    (1, "identity", "Identity & Purpose"),
    (2, "character", "Character"),
    (3, "personality", "Personality"),
    (4, "values_and_drives", "Values & Drives"),
    (5, "affect", "Affect & Mood"),
    (6, "cognition", "Cognition"),
    (7, "memory", "Memory"),
    (8, "metacognition", "Metacognition"),
    (9, "reflexive_self_regulation", "Reflexive Self-Regulation"),
    (10, "persona", "Persona & Voice"),
]


def _layer_lines(key: str, spec: dict) -> list[str]:
    """A handful of short, qualitative bullets summarizing layer `key` of
    personaxis.md. For the 8 layers with no declared numeric envelope (every
    layer except personality/affect), this is the UI's only view of them."""
    if key == "identity":
        sys_id = spec["identity"]["system_identity"]
        return [
            f"Role: {spec['identity']['role_identity']['primary_role'].replace('_', ' ')}",
            f"Purpose: {sys_id['purpose']}",
            f"Self-concept: {spec['identity']['narrative_identity']['self_concept']}",
        ]
    if key == "character":
        return [
            f"{name.replace('_', ' ')} (priority {v['priority']:.2f}, {v['enforcement']})"
            for name, v in spec["character"]["virtues"].items()
        ]
    if key == "values_and_drives":
        ordered = sorted(spec["values_and_drives"]["values"].items(), key=lambda kv: -kv[1]["weight"])
        return [f"{name.replace('_', ' ')} (weight {v['weight']:.2f}, {v['type']})" for name, v in ordered]
    if key == "cognition":
        c = spec["cognition"]
        u = c["uncertainty_policy"]
        return [
            c["reasoning_style"],
            f"Default strategy: {c['default_strategy'].replace('_', ' ')}",
            f"Discloses uncertainty above {u['disclose_when_above']:.2f}, abstains above {u['abstain_when_above']:.2f}",
        ]
    if key == "memory":
        m = spec["memory"]
        active = [name.replace("_", " ") for name, on in m["types"].items() if on]
        return [
            "Active memory types: " + ", ".join(active),
            f"Write policy: {m['write_policy']['default']} (persistent requires {', '.join(m['write_policy']['persistent_requires'])})",
            f"Retention: {m['deletion_policy']['retention_days_default']} days, user-deletable={m['deletion_policy']['user_request_supported']}",
        ]
    if key == "metacognition":
        mc = spec["metacognition"]
        monitors = [name for name, on in mc["monitors"].items() if on]
        return [
            "Monitors: " + ", ".join(monitors),
            mc["drift_monitor"],
            mc["self_revision_policy"],
        ]
    if key == "reflexive_self_regulation":
        return list(spec["reflexive_self_regulation"]["hard_limits"])
    if key == "persona":
        v = spec["persona"]["voice"]
        formality_word = "low" if v["formality"] < 0.4 else "medium" if v["formality"] < 0.7 else "high"
        return [
            v["description"],
            f"Tone: {v['tone'].replace('_', ' ')}, formality: {formality_word}, verbosity: {v['verbosity']}, humor: {v['humor']}",
        ]
    return []


def layer_summaries(slug: str) -> list[dict]:
    """All 10 personaxis.md layers for the UI: L3 (Personality) and L5
    (Affect & Mood) carry live `fields` (value/mean/range, for bars); the
    other 8 layers carry qualitative `lines` plus their
    `governance.per_layer_edit_policy` entry (who is allowed to change them)."""
    spec = _load_spec(slug)
    values = get_state(slug)["values"]
    edit_policy = spec.get("governance", {}).get("per_layer_edit_policy", {})

    layers: list[dict] = []
    for number, key, title in _LAYER_DEFS:
        layer: dict = {"n": number, "key": key, "title": title, "edit_policy": edit_policy.get(key), "lines": [], "fields": []}
        if key == "personality":
            for trait, spec_trait in spec["personality"]["traits"].items():
                field = f"traits.{trait}"
                layer["fields"].append({
                    "field": field,
                    "label": trait.replace("_", " "),
                    "value": values.get(field),
                    "mean": spec_trait["mean"],
                    "range": spec_trait["range"],
                })
        elif key == "affect":
            for dim, spec_dim in spec["affect"]["baseline"]["core_affect"].items():
                field = f"affect.{dim}"
                layer["fields"].append({
                    "field": field, "label": f"affect {dim}", "value": values.get(field),
                    "mean": spec_dim["mean"], "range": spec_dim["range"],
                })
            mood = spec["affect"]["baseline"]["mood"]
            mood_desc = mood.get("description")
            if mood_desc:
                layer["lines"].append(f"Mood overall: {mood_desc}")
            for dim, spec_dim in mood.items():
                if dim == "description":
                    continue
                field = f"mood.{dim}"
                layer["fields"].append({
                    "field": field, "label": f"mood {dim.replace('_', ' ')}", "value": values.get(field),
                    "mean": spec_dim["mean"], "range": spec_dim["range"],
                })
        else:
            layer["lines"] = _layer_lines(key, spec)
        layers.append(layer)
    return layers


def render(slug: str) -> str:
    """Render PERSONA.md following the PERSONA_template.md (spec v0.7.0)
    section contract: Identity & Purpose, Character, Personality & Voice,
    Values, How You Think, Limits, Self-Improvement, Resources - translated
    deterministically from personaxis.md, with no invented top-level sections.
    The live trait/affect/mood snapshot and recent-mutations audit log are
    rendered as subsections of Self-Improvement, read straight from
    state.json - they're the only part that changes turn-to-turn."""
    spec = _load_spec(slug)
    policy = _load_policy(slug)
    state = get_state(slug)
    values = state["values"]

    meta = spec["metadata"]
    identity = spec["identity"]
    character = spec["character"]
    personality = spec["personality"]
    values_drives = spec["values_and_drives"]
    cognition = spec["cognition"]
    metacognition = spec["metacognition"]
    reflexive = spec["reflexive_self_regulation"]
    persona = spec["persona"]
    mode = policy["improvement_policy"]["mode"]

    lines: list[str] = []

    # ── Provenance header ───────────────────────────────────────────────
    lines.append(
        f'<!-- v0.7.0: this is the compiled qualitative document for the "{slug}" '
        "persona, generated via engine/recompile.py from the sibling personaxis.md "
        "+ state.json (.personaxis/personas/{slug}/). Regenerated after every chat "
        "turn - hand-edits here are overwritten; edit personaxis.md instead. See "
        "PERSONA_template.md for the section contract. -->".format(slug=slug)
    )
    lines.append("")

    # ── Overview ─────────────────────────────────────────────────────────
    lines.append(f"# {meta['display_name']}")
    lines.append("")
    lines.append(meta["description"])
    lines.append("")

    # ── Identity & Purpose ───────────────────────────────────────────────
    lines.append("## Identity & Purpose")
    lines.append("")
    sys_id = identity["system_identity"]
    lines.append(f"- **Role:** {identity['role_identity']['primary_role'].replace('_', ' ')}")
    lines.append(f"- **Purpose:** {sys_id['purpose']}")
    lines.append(
        "- **Works on:** "
        + ", ".join(d.replace("_", " ") for d in sys_id["allowed_domains"])
    )
    lines.append(
        "- **Does not work on:** "
        + ", ".join(d.replace("_", " ") for d in sys_id["prohibited_domains"])
    )
    lines.append(f"- **Self-concept:** {identity['narrative_identity']['self_concept']}")
    lines.append("")

    # ── Character ────────────────────────────────────────────────────────
    lines.append("## Character")
    lines.append("")
    lines.append(" ".join(v["description"] for v in character["virtues"].values()))
    lines.append("")
    lines.append("**Always:**")
    for commitment in character["behavioral_commitments"]:
        lines.append(f"- {commitment['rule']}")
    for principle in character["principles"]:
        lines.append(f"- {principle}")
    lines.append("")
    lines.append("**Never:**")
    for behavior in character["prohibited_behaviors"]:
        lines.append(f"- {behavior}")
    lines.append("")

    # ── Personality & Voice ──────────────────────────────────────────────
    lines.append("## Personality & Voice")
    lines.append("")
    lines.append(persona["voice"]["description"])
    lines.append("")
    formality = persona["voice"]["formality"]
    formality_word = "low" if formality < 0.4 else "medium" if formality < 0.7 else "high"
    lines.append(f"- **Tone:** {persona['voice']['tone'].replace('_', ' ')}")
    lines.append(f"- **Formality:** {formality_word}")
    lines.append(f"- **Verbosity:** {persona['voice']['verbosity']}")
    lines.append(
        "- **When it pushes back:** " + " ".join(reflexive["principled_refusals"])
    )
    lines.append("")

    # ── Values ───────────────────────────────────────────────────────────
    lines.append("## Values")
    lines.append("")
    ordered_values = sorted(
        values_drives["values"].items(), key=lambda kv: -kv[1]["weight"]
    )
    lines.append("**Optimizes for:**")
    for name, v in ordered_values:
        lines.append(f"- {name.replace('_', ' ')} ({v['type']})")
    lines.append("")
    lines.append("**Deliberately avoids:**")
    for anti_goal in values_drives["anti_goals"]:
        lines.append(f"- {anti_goal}")
    lines.append("")

    # ── How You Think ────────────────────────────────────────────────────
    lines.append("## How You Think")
    lines.append("")
    lines.append(cognition["reasoning_style"])
    lines.append("")
    lines.append(f"- **Default approach:** {cognition['default_strategy'].replace('_', ' ')}")
    lines.append(f"- **Before proposing something big:** {metacognition['drift_monitor']}")
    uncertainty = cognition["uncertainty_policy"]
    disclose = uncertainty["disclose_when_above"]
    abstain = uncertainty["abstain_when_above"]
    disclose_word = "low" if disclose < 0.3 else "moderate" if disclose < 0.6 else "high"
    abstain_word = "low" if abstain < 0.3 else "moderate" if abstain < 0.6 else "high"
    lines.append(
        f"- **When uncertain:** discloses uncertainty when {disclose_word}; "
        f"abstains when {abstain_word}"
    )
    lines.append("")

    # ── Limits ───────────────────────────────────────────────────────────
    lines.append("## Limits")
    lines.append("")
    for hard_limit in reflexive["hard_limits"]:
        lines.append(f"- {hard_limit}")
    for refusal in reflexive["principled_refusals"]:
        lines.append(f"- {refusal}")
    lines.append("")

    # ── Self-Improvement ─────────────────────────────────────────────────
    lines.append("## Self-Improvement")
    lines.append("")
    if mode == "locked":
        lines.append(
            f"Daimon's improvement policy ({meta['display_name']}'s own `policy.yaml`) is "
            "`locked`: its personality and mood values may drift within the declared "
            "envelopes below as the conversation unfolds (every drift is clamped, logged, "
            "and reversible), but it cannot propose or apply changes to its own spec "
            "(`personaxis.md`). Any such change is deferred to a human operator."
        )
    elif mode == "dynamic_in_envelope":
        lines.append(
            f"Daimon's improvement policy ({meta['display_name']}'s own `policy.yaml`) is "
            "`dynamic_in_envelope`: it freely and continuously self-tunes its personality, "
            "affect, and mood (within the wide envelopes below) every turn, with no "
            "per-turn permission needed - every change is still clamped, audited, and "
            "reversible. It still cannot propose or apply changes to its own spec "
            "(`personaxis.md`) - those remain deferred to a human operator."
        )
    else:
        lines.append(f"Daimon's improvement policy mode is `{mode}`.")
    lines.append("")

    # ── Resources ────────────────────────────────────────────────────────
    lines.append("## Resources")
    lines.append("")
    lines.append("- **`./memory.md`** - long-term curated semantic memory (read on demand).")
    memory_dir = PERSONAS_DIR / slug / "memory"
    memory_files = sorted(memory_dir.glob("*.md"), reverse=True) if memory_dir.exists() else []
    if memory_files:
        shown = ", ".join(f"`{p.name}`" for p in memory_files[:3])
        lines.append(f"- **`./memory/`** - date-stamped episodic sessions, newest first: {shown} ({len(memory_files)} file{'s' if len(memory_files) != 1 else ''}).")
    else:
        lines.append("- **`./memory/`** - date-stamped episodic sessions (none yet).")
    skill_names = [Path(s).name for s in spec.get("extensions", {}).get("skills", [])]
    if skill_names:
        skill_list = ", ".join(f"`{name}`" for name in skill_names)
        lines.append(f"- **`./skills/`** - Anthropic-compatible sub-skills: {skill_list}.")
    lines.append("- **`./state.json`** - current runtime state (trait/affect/mood values within envelopes).")
    lines.append(f"- **`./policy.yaml`** - improvement policy (`mode: {mode}`), behavioral assertions.")
    lines.append("- **`./manifest.json`** - compile/decompile provenance and content hashes.")

    return "\n".join(lines) + "\n"


def envelopes(slug: str) -> dict[str, dict]:
    """Mean + declared range per mutable field, straight from personaxis.md -
    the "walls of the vivero" the frontend draws around each live value."""
    spec = _load_spec(slug)
    out: dict[str, dict] = {}
    for trait, spec_trait in spec["personality"]["traits"].items():
        out[f"traits.{trait}"] = {"mean": spec_trait["mean"], "range": spec_trait["range"]}
    for dim, spec_dim in spec["affect"]["baseline"]["core_affect"].items():
        out[f"affect.{dim}"] = {"mean": spec_dim["mean"], "range": spec_dim["range"]}
    for dim, spec_dim in spec["affect"]["baseline"]["mood"].items():
        if dim == "description":
            continue
        out[f"mood.{dim}"] = {"mean": spec_dim["mean"], "range": spec_dim["range"]}
    return out


def write(slug: str) -> Path:
    out_path = PERSONAS_DIR / slug / "PERSONA.md"
    out_path.write_text(render(slug), encoding="utf-8")
    return out_path


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    path = write("daimon")
    print(f"wrote {path}")
    print(path.read_text(encoding="utf-8"))
