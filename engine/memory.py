"""Step 6 of the living loop: curated memory (F2, v4).

Durable, consolidated knowledge - NOT a transcript. The raw chat transcript
itself is owned entirely by `gr.Chatbot`'s session history (passed into
`engine.loop.build_messages()` for multi-turn coherence); this module never
stores a copy of it. Since Daimon runs 100% on a local model, the extra
curation call is free, so both files are rewritten by `curate_memory()`
after every turn:

  - `memory.md` - cross-session long-term memory: `## User profile`,
    `## Stable preferences and behavioral patterns`,
    `## Notable interactions`.
  - `memory/<date>.md` - this session's consolidated summary: YAML
    frontmatter (`date`, `session_id`) + `## episodic`,
    `## user_preferences`, `## procedural`, `## autobiographical`.
"""

from __future__ import annotations

import re
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from engine.spec_bridge import PERSONAS_DIR  # noqa: E402

# Guards against a small model echoing the prompt/turn back as "content":
# if any of these show up in the output, treat it as a malformed reply and
# leave the memory file untouched rather than corrupt it.
_BAD_MARKERS = ("new turn:", "current sections:", "your reply:", "user:", "daimon:")

# Both curation prompts ask the model for ONLY the bullet sections (not the
# header/frontmatter, which are deterministic and applied by Python below) -
# a 1B model is unreliable at reproducing boilerplate verbatim, so we never
# ask it to.
_LONG_TERM_SECTIONS = ("User profile", "Stable preferences and behavioral patterns", "Notable interactions")
_EPISODIC_SECTIONS = ("episodic", "user_preferences", "procedural", "autobiographical")

_LONG_TERM_SYSTEM_PROMPT = (
    "You maintain Daimon's long-term memory: durable, cross-session "
    "knowledge about the USER and this relationship - NOT a transcript.\n\n"
    "Output ONLY these 3 sections, each a bullet list of at most 4 bullets, "
    "each under 15 words:\n\n"
    "## User profile\n- ...\n\n"
    "## Stable preferences and behavioral patterns\n- ...\n\n"
    "## Notable interactions\n- ...\n\n"
    "You will see the CURRENT sections and ONE new turn. If the turn reveals "
    "a new durable fact (about the user, their preferences, or a notable "
    "refusal/boundary moment), output the updated sections (same 3, in "
    "order, each trimmed to at most 4 bullets - drop the oldest/least "
    "useful first). If nothing durable changed, reply with exactly: "
    "NO_CHANGE\n\n"
    "Example reply:\n"
    "## User profile\n- User is named Ana, a veterinarian.\n\n"
    "## Stable preferences and behavioral patterns\n- Prefers short, direct answers.\n\n"
    "## Notable interactions\n- (none yet)"
)

_EPISODIC_SYSTEM_PROMPT = (
    "You maintain Daimon's consolidated session summary for today - a "
    "narrative summary of THIS conversation so far, NOT a transcript.\n\n"
    "Output ONLY these 4 sections, each a bullet list of at most 5 bullets, "
    "each under 20 words:\n\n"
    "## episodic\n- what happened this session (events, topics, outcomes)\n\n"
    "## user_preferences\n- preferences the user expressed this session\n\n"
    "## procedural\n- how Daimon should act/respond going forward, learned this session\n\n"
    "## autobiographical\n- what Daimon itself did/decided/felt this session\n\n"
    "You will see the CURRENT sections and ONE new turn. Output the updated "
    "sections (same 4, in order, each trimmed to at most 5 bullets - drop "
    "the oldest/least useful first). If the turn adds nothing to any "
    "section, reply with exactly: NO_CHANGE"
)

_FENCE_RE = re.compile(r"^```\w*\s*$", re.MULTILINE)

# A small model occasionally echoes a section header back as if it were a
# bullet (e.g. "- User profile" inside "## Notable interactions") - drop
# bullets that are just one of our own header names.
_KNOWN_HEADERS = {h.lower() for h in _LONG_TERM_SECTIONS + _EPISODIC_SECTIONS}


def _extract_section_bullets(text: str, header: str, limit: int) -> list[str]:
    """Return up to `limit` '- ' bullet lines found under `## {header}` in
    `text` (case-sensitive header match, stops at the next `## ` or EOF)."""
    pattern = re.compile(rf"^## {re.escape(header)}\s*\n(.*?)(?=\n## |\Z)", re.DOTALL | re.MULTILINE)
    m = pattern.search(text)
    if not m:
        return []
    bullets = [ln.strip() for ln in m.group(1).splitlines() if ln.strip().startswith("- ")]
    bullets = [b for b in bullets if b.lower() not in ("- (none yet)", "- ...")]
    bullets = [b for b in bullets if b[2:].strip().lower() not in _KNOWN_HEADERS]
    return bullets[:limit]


def _memory_dir(slug: str) -> Path:
    path = PERSONAS_DIR / slug / "memory"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _memory_md_path(slug: str) -> Path:
    return PERSONAS_DIR / slug / "memory.md"


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _episodic_path(slug: str) -> Path:
    return _memory_dir(slug) / f"{_today()}.md"


def _rebuild(sections: tuple[str, ...], preamble: str, current: str, model_out: str, limit: int) -> tuple[str, bool]:
    """Deterministically reassemble a curated memory file from `preamble`
    (header/frontmatter, never written by the model) plus, for each
    section, whichever bullet list is non-empty between the model's
    proposal and the current file (the model's proposal wins; if it left a
    section out entirely, the old bullets for that section are kept)."""
    changed = False
    lines = [preamble.rstrip(), ""]
    for header in sections:
        old = _extract_section_bullets(current, header, limit)
        new = _extract_section_bullets(model_out, header, limit)
        bullets = new or old
        if bullets != old:
            changed = True
        lines.append(f"## {header}")
        lines.extend(bullets if bullets else ["- (none yet)"])
        lines.append("")
    return "\n".join(lines).rstrip() + "\n", changed


def _curate_file(
    path: Path,
    *,
    system_prompt: str,
    sections: tuple[str, ...],
    limit: int,
    preamble: str,
    user_message: str,
    reply: str,
    max_tokens: int,
) -> bool:
    """Show the model the CURRENT bullet sections of `path` plus one new
    turn, and let it propose updated sections (not the whole file - the
    header/frontmatter is reapplied deterministically by `_rebuild`).
    Returns True if `path` was rewritten. Best-effort: any model/parsing
    failure or no-op proposal leaves `path` untouched."""
    from model.client import chat  # local import: keep memory.py importable without a model server

    current = path.read_text(encoding="utf-8") if path.exists() else ""
    current_sections = "\n\n".join(
        f"## {header}\n" + "\n".join(_extract_section_bullets(current, header, limit) or ["- (none yet)"])
        for header in sections
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": (
                f"Current sections:\n{current_sections}\n\n"
                f"New turn:\nUser: {user_message}\nDaimon: {reply}\n\n"
                "Your reply:"
            ),
        },
    ]
    try:
        out = chat(messages, modality="text", max_tokens=max_tokens, temperature=0.1, enable_thinking=False)
    except Exception:
        return False

    out = _FENCE_RE.sub("", (out or "")).strip()
    if not out or out.upper().startswith("NO_CHANGE"):
        return False
    if any(marker in out.lower() for marker in _BAD_MARKERS):
        return False  # model echoed the prompt back - don't corrupt the file

    new_text, changed = _rebuild(sections, preamble, current, out, limit)
    if not changed:
        return False
    path.write_text(new_text, encoding="utf-8")
    return True


def curate_memory(slug: str, user_message: str, reply: str) -> dict[str, bool]:
    """Let the local model update both curated-memory files for the new
    turn: `memory.md` (cross-session) and `memory/<date>.md` (today's
    consolidated summary). Returns which files actually changed."""
    long_term_changed = _curate_file(
        _memory_md_path(slug),
        system_prompt=_LONG_TERM_SYSTEM_PROMPT,
        sections=_LONG_TERM_SECTIONS,
        limit=4,
        preamble="# Daimon - long-term memory",
        user_message=user_message,
        reply=reply,
        max_tokens=200,
    )
    episodic_changed = _curate_file(
        _episodic_path(slug),
        system_prompt=_EPISODIC_SYSTEM_PROMPT,
        sections=_EPISODIC_SECTIONS,
        limit=5,
        preamble=f"---\ndate: {_today()}\nsession_id: {slug}-{_today()}\n---",
        user_message=user_message,
        reply=reply,
        max_tokens=300,
    )
    return {"memory.md": long_term_changed, f"memory/{_today()}.md": episodic_changed}
