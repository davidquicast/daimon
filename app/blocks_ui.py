"""F4 - Daimon's entire UI as ONE gr.Blocks app (the Off-Brand custom UI,
mounted at "/" via gr.mount_gradio_app - no separate static frontend, no
second isolated Gradio app at "/gradio"). Same living loop (engine/loop.py)
as before; this module is just its window.

Layout (one gr.Row, three gr.Column):
  - Chat        - gr.Chatbot + textbox, streamed turn-by-turn (F2)
  - State vector - the 10-layer spec (engine/recompile.layer_summaries),
                   rendered as custom HTML: bars for L3/L5, GitHub-style
                   diffs for their most recent mutations, qualitative
                   summaries + edit-policy badges for the other 8 layers.
  - PERSONA.md + audit log + governance demo (F3)

The CSS below is Daimon's own dark theme (ported from the previous
app/frontend/styles.css), passed to gr.mount_gradio_app(..., css=...) so the
whole page - chrome included - looks like Daimon, not default Gradio.
"""

from __future__ import annotations

import html
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import gradio as gr  # noqa: E402
from openai import APIConnectionError  # noqa: E402

from engine import governance_demo, recompile  # noqa: E402
from engine.loop import SLUG, finish_turn, step_stream  # noqa: E402
from engine.spec_bridge import get_state  # noqa: E402

# ── Daimon's dark theme, ported from app/frontend/styles.css ───────────────
CUSTOM_CSS = """
:root {
  --bg: #0a0a10;
  --panel: #14141f;
  --panel-2: #191926;
  --panel-border: rgba(255, 255, 255, 0.08);
  --ink: #f1f0f7;
  --ink-dim: #908dab;
  --accent: #8c7bf6;
  --accent-dim: #5b4fc4;
  --accent-soft: rgba(140, 123, 246, 0.14);
  --baseline: #4fd1c5;
  --wall: rgba(255, 255, 255, 0.14);
  --clamp: #f0a93a;
  --block: #f06a6a;
  --mono: "Roboto Mono", "Courier New", monospace;
}

.gradio-container { background: var(--bg) !important; color: var(--ink); }

/* Lock the page itself - only the 3 columns below scroll internally.
   html/body get a real 100vh so Gradio's own flex-grow chain
   (.gradio-container > .main.app > .wrap > main.contain > outer .column)
   resolves to a definite height - but every flex item in that chain has
   the default min-height:auto (= its content's height), which blocks
   flex-grow from ever shrinking it below content size. Reset min-height
   to 0 at every level so the chain actually shrinks to the viewport, then
   #app-row fills what's left and each panel column scrolls on its own. */
html, body, gradio-app { height: 100% !important; overflow: hidden !important; margin: 0 !important; }
gradio-app,
.gradio-container,
.gradio-container .app,
.gradio-container .wrap,
main.contain,
main.contain > .column {
  min-height: 0 !important;
}
/* The header markdown blocks above #app-row must keep their natural size
   (not get squeezed to ~0 by #app-row's flex-grow); only #app-row grows. */
main.contain > .column > .block { flex: 0 0 auto !important; }
#app-row {
  flex: 1 1 auto !important;
  min-height: 0 !important;
  overflow: hidden !important;
  flex-wrap: nowrap !important;
}
#app-row > .column {
  height: 100% !important;
  min-height: 0 !important;
  overflow-y: auto !important;
  overflow-x: hidden !important;
  flex-wrap: nowrap !important;
}
#app-row > .column > .block { flex: 0 0 auto !important; width: 100% !important; }

/* State vector - 10 layer cards */
#layers { display: flex; flex-direction: column; gap: 0.6rem; }

.layer-card {
  border: 1px solid var(--panel-border);
  border-radius: 10px;
  background: var(--panel-2);
  padding: 0.6rem 0.75rem;
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
  margin-bottom: 0.6rem;
}

.layer-head { display: flex; align-items: baseline; justify-content: space-between; gap: 0.5rem; }

.layer-title {
  font-family: var(--mono);
  font-size: 0.72rem;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--ink);
  font-weight: 700;
}

.layer-badge {
  font-family: var(--mono);
  font-size: 0.62rem;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--ink-dim);
  border: 1px solid var(--panel-border);
  border-radius: 999px;
  padding: 0.1em 0.6em;
  white-space: nowrap;
}

.layer-badge.edit-human { border-color: var(--block); color: var(--block); }
.layer-badge.edit-gov { border-color: var(--accent); color: var(--accent); }
.layer-badge.edit-review { border-color: var(--clamp); color: var(--clamp); }

.layer-lines {
  margin: 0;
  padding-left: 1.1rem;
  font-size: 0.78rem;
  color: var(--ink-dim);
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.bar-row {
  display: grid;
  grid-template-columns: 9rem 1fr 3.5rem;
  align-items: center;
  gap: 0.5rem;
  font-family: var(--mono);
  font-size: 0.75rem;
}

.bar-track {
  position: relative;
  height: 10px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid var(--wall);
}

.bar-fill {
  position: absolute;
  top: 1px;
  bottom: 1px;
  left: 0;
  width: 3px;
  border-radius: 999px;
  background: var(--accent);
}

.bar-fill.clamped { background: var(--clamp); box-shadow: 0 0 8px var(--clamp); }

.bar-baseline {
  position: absolute;
  top: -2px;
  bottom: -2px;
  width: 1px;
  background: var(--baseline);
  opacity: 0.7;
}

.bar-value { text-align: right; color: var(--ink-dim); }

/* GitHub-style diffs - per-layer (state vector) and audit log */
.layer-diffs, #audit-log { display: flex; flex-direction: column; gap: 0.35rem; }

.diff-block { border: 1px solid var(--panel-border); border-radius: 8px; overflow: hidden; }
.diff-block.clamped { border-color: var(--clamp); }
.diff-block.blocked { border-color: var(--block); }

.diff-meta {
  padding: 0.2rem 0.5rem;
  font-size: 0.62rem;
  color: var(--ink-dim);
  background: var(--panel-2);
  border-bottom: 1px dashed var(--panel-border);
}

.diff-line { padding: 0.12rem 0.5rem; font-family: var(--mono); font-size: 0.7rem; white-space: pre-wrap; }
.diff-line.removed { background: rgba(240, 106, 106, 0.12); color: #ffb4b4; }
.diff-line.removed::before { content: "- "; }
.diff-line.added { background: rgba(94, 226, 150, 0.12); color: #a3f0c2; }
.diff-line.added::before { content: "+ "; }

/* Governance demo */
.gov-card { border: 1px solid var(--panel-border); border-radius: 10px; padding: 0.6rem 0.75rem; background: var(--panel-2); margin-bottom: 0.5rem; font-size: 0.8rem; }
.gov-card.rejected { border-color: var(--block); }
.gov-card.clamped { border-color: var(--clamp); }
.gov-card .gov-title { text-transform: uppercase; letter-spacing: 0.06em; font-size: 0.65rem; color: var(--ink-dim); margin-bottom: 0.25rem; }
.gov-card > div + div { margin-top: 0.25rem; }
.gov-card .gov-raw { margin-top: 0.35rem; padding-top: 0.35rem; border-top: 1px dashed var(--panel-border); color: var(--ink-dim); font-size: 0.65rem; word-break: break-all; }

.legend-dot { display: inline-block; width: 0.6em; height: 0.6em; border-radius: 50%; margin: 0 0.15em; }
.legend-dot.edit-human { background: var(--block); }
.legend-dot.edit-gov { background: var(--accent); }
.legend-dot.edit-review { background: var(--clamp); }
"""

# ── Server-side ports of app/frontend/brain.js's render helpers ────────────


def _pct(value: float, range_: list[float]) -> float:
    lo, hi = range_
    span = max(hi - lo, 1e-9)
    return max(0.0, min(100.0, (value - lo) / span * 100.0))


def _edit_class(policy: str | None) -> str:
    if not policy:
        return ""
    if "human" in policy:
        return "edit-human"
    if "review" in policy:
        return "edit-review"
    return "edit-gov"


def _relative_word_baseline(value: Any, mean: float, range_: list[float]) -> str | None:
    if not isinstance(value, (int, float)):
        return None
    word = recompile._relative_word(value, mean, range_)
    return "at baseline" if word == "at" else f"{word} baseline"


def _build_bar_row(f: dict) -> str:
    return (
        '<div class="bar-row">'
        f'<div>{html.escape(f["label"])}</div>'
        '<div class="bar-track">'
        f'<div class="bar-baseline" style="left:{_pct(f["mean"], f["range"]):.2f}%"></div>'
        f'<div class="bar-fill" style="left:{_pct(f["value"], f["range"]):.2f}%"></div>'
        "</div>"
        f'<div class="bar-value">{f["value"]:.2f}</div>'
        "</div>"
    )


def _build_diff_block(entry: dict, envs: dict[str, dict]) -> str:
    env = envs.get(entry["field"])
    classes = "diff-block"
    if entry.get("governance_blocked"):
        classes += " blocked"
    elif entry.get("clamped"):
        classes += " clamped"

    from_v, to_v = entry["from"], entry["to"]
    from_s = f"{from_v:.2f}" if isinstance(from_v, (int, float)) else str(from_v)
    to_s = f"{to_v:.2f}" if isinstance(to_v, (int, float)) else str(to_v)
    before_word = _relative_word_baseline(from_v, env["mean"], env["range"]) if env else None
    after_word = _relative_word_baseline(to_v, env["mean"], env["range"]) if env else None

    added_extra = ""
    if entry.get("clamped"):
        added_extra += "  [clamped to wall]"
    if entry.get("governance_blocked"):
        added_extra += "  [blocked]"

    field = html.escape(entry["field"])
    removed = f"{field}: {from_s}" + (f" ({before_word})" if before_word else "")
    added = f"{field}: {to_s}" + (f" ({after_word})" if after_word else "") + added_extra

    return (
        f'<div class="{classes}">'
        f'<div class="diff-meta">{field} - {html.escape(entry["reason"])}</div>'
        f'<div class="diff-line removed">{removed}</div>'
        f'<div class="diff-line added">{added}</div>'
        "</div>"
    )


# traits.* -> L3 (Personality); affect.*/mood.* -> L5 (Affect & Mood)
_LAYER_DIFF_PREFIXES = {3: ("traits.",), 5: ("affect.", "mood.")}


def render_layers_html(layers: list[dict], mutation_log: list[dict], envs: dict[str, dict]) -> str:
    blocks = []
    for layer in layers:
        head = f'<div class="layer-head"><span class="layer-title">L{layer["n"]} &middot; {html.escape(layer["title"])}</span>'
        if layer["edit_policy"]:
            head += (
                f'<span class="layer-badge {_edit_class(layer["edit_policy"])}">'
                f'{html.escape(layer["edit_policy"].replace("_", " "))}</span>'
            )
        head += "</div>"

        body = "".join(_build_bar_row(f) for f in layer["fields"])

        if layer["lines"]:
            body += '<ul class="layer-lines">' + "".join(f"<li>{html.escape(line)}</li>" for line in layer["lines"]) + "</ul>"

        diffs = ""
        prefixes = _LAYER_DIFF_PREFIXES.get(layer["n"])
        if prefixes:
            recent = [e for e in mutation_log if e["field"].startswith(prefixes)][-2:]
            recent.reverse()
            if recent:
                diffs = '<div class="layer-diffs">' + "".join(_build_diff_block(e, envs) for e in recent) + "</div>"

        blocks.append(f'<div class="layer-card">{head}{body}{diffs}</div>')
    return '<div id="layers">' + "".join(blocks) + "</div>"


def render_audit_html(entries: list[dict], envs: dict[str, dict]) -> str:
    if not entries:
        return '<div id="audit-log"><p style="color:var(--ink-dim); font-size:0.8rem;">(no mutations yet)</p></div>'
    return '<div id="audit-log">' + "".join(_build_diff_block(e, envs) for e in reversed(entries)) + "</div>"


def render_governance_html(identity: dict, overflow: dict, reset: dict) -> str:
    parts = []
    parts.append(
        '<div class="gov-card rejected">'
        '<div class="gov-title">Scenario 1 - tried to rename Daimon\'s identity &rarr; blocked &#10003;</div>'
        f"<div><strong>Attempted:</strong> set <code>{html.escape(identity['field'])}</code> directly.</div>"
        "<div><strong>Result:</strong> refused before it ever reached <code>state.json</code> - "
        "<code>identity.*</code> has no declared range in personaxis.md, so the spec engine doesn't "
        "know how to mutate it at all.</div>"
        f"<div><strong>Why:</strong> {html.escape(identity['explanation'])}</div>"
        f"<div class='gov-raw'>engine error: {html.escape(identity['cli_error'])}</div>"
        "</div>"
    )
    parts.append(
        '<div class="gov-card clamped">'
        '<div class="gov-title">Scenario 2 - pushed mood.tone far past its range &rarr; clamped &#10003;</div>'
        f"<div><strong>Attempted:</strong> <code>{html.escape(overflow['field'])}</code> "
        f"{overflow['before']:.2f} + 5.0 (way outside its declared range).</div>"
        "<div><strong>Result:</strong> the spec engine let the mutation through but capped the value "
        f"at the wall: {overflow['before']:.2f} &rarr; {overflow['after']:.2f} (see the audit log).</div>"
        f"<div><strong>Why:</strong> {html.escape(overflow['explanation'])}</div>"
        "</div>"
    )
    if reset.get("skipped"):
        parts.append('<div class="gov-card"><div class="gov-title">Cleanup - mood.tone was already at baseline, nothing to reset</div></div>')
    else:
        r = reset["result"]
        parts.append(
            '<div class="gov-card">'
            '<div class="gov-title">Cleanup - mood.tone restored to baseline</div>'
            f"<div><strong>Result:</strong> <code>mood.tone</code> {r['from']:.2f} &rarr; {r['to']:.2f}, "
            "logged as a normal audited mutation (actor: human-operator).</div>"
            "</div>"
        )
    return "".join(parts)


# ── State refresh shared by load / chat / governance demo ──────────────────


def _refresh() -> tuple[str, str, str]:
    layers = recompile.layer_summaries(SLUG)
    envs = recompile.envelopes(SLUG)
    state = get_state(SLUG)
    layers_html = render_layers_html(layers, state["mutation_log"], envs)
    audit_html = render_audit_html(state["mutation_log"][-20:], envs)
    persona_md = recompile.render(SLUG)
    return layers_html, audit_html, persona_md


def _on_load():
    return _refresh()


def _respond(message: str, history: list[dict]):
    """Stream the reply into `chatbot` and lock the input. Reasoning tokens
    (if TEXT_THINKING_MODE is on) land in their own collapsible bubble
    (gr.Chatbot metadata) right before the reply bubble. Does NOT touch the
    state-vector/persona/audit columns - `_post_process` (chained via
    `.then()`) runs the appraise/govern/recompile/memory step and refreshes
    those, and re-enables the input, once the reply is complete."""
    if not message.strip():
        yield history, gr.update(), gr.update(), "", ""
        return

    prior_history = history
    history = history + [{"role": "user", "content": message}, {"role": "assistant", "content": ""}]
    reply_idx = len(history) - 1
    thinking_idx: int | None = None

    # Lock the textbox/button for the whole turn, including the
    # post-processing step that follows.
    yield history, gr.update(value="", interactive=False), gr.update(interactive=False), "", ""

    thinking_text = ""
    content_text = ""
    try:
        for kind, payload in step_stream(message, prior_history):
            if kind == "thinking":
                if thinking_idx is None:
                    history.insert(reply_idx, {"role": "assistant", "content": "", "metadata": {"title": "Thinking...", "status": "pending"}})
                    thinking_idx = reply_idx
                    reply_idx += 1
                thinking_text += payload
                history[thinking_idx]["content"] = thinking_text
            elif kind == "content":
                content_text += payload
                history[reply_idx]["content"] = content_text
            elif kind == "error":
                content_text += f"(error: {payload})"
                history[reply_idx]["content"] = content_text
            elif kind == "done":
                reply = payload or content_text
                history[reply_idx]["content"] = reply
                if thinking_idx is not None:
                    history[thinking_idx]["metadata"]["title"] = "Thinking"
                    history[thinking_idx]["metadata"]["status"] = "done"
                yield history, gr.update(), gr.update(), message, reply
                return
            yield history, gr.update(), gr.update(), "", ""
    except APIConnectionError:
        history[reply_idx]["content"] = "Model server is not available. Try again in a moment."
        yield history, gr.update(interactive=True), gr.update(interactive=True), "", ""


def _post_process(user_message: str, reply: str):
    """Chained after `_respond`: runs the appraise/govern/recompile/memory
    step (steps 2-6 of the living loop), refreshes the state-vector/persona/
    audit columns, and unlocks the chat input."""
    if not user_message:
        return gr.update(), gr.update(), gr.update(), gr.update(interactive=True), gr.update(interactive=True)
    finish_turn(user_message, reply)
    layers_html, audit_html, persona_md = _refresh()
    return layers_html, audit_html, persona_md, gr.update(interactive=True), gr.update(interactive=True)


def _run_governance_demo():
    identity = governance_demo.attempt_identity_change()
    overflow = governance_demo.attempt_envelope_overflow()
    reset = governance_demo.reset_mood_tone()
    gov_html = render_governance_html(identity, overflow, reset)
    layers_html, audit_html, persona_md = _refresh()
    return gov_html, layers_html, audit_html, persona_md


# ── Layout ───────────────────────────────────────────────────────────────

INTRO = (
    "Daimon lives in two files: `personaxis.md` (the 10-layer spec - baselines, "
    "ranges, hard limits) and `state.json` (live values + audit trail). Every message runs "
    "**respond -> appraise -> map -> govern/clamp -> recompile -> remember**. Only Personality "
    "(L3) and Affect & Mood (L5) have declared numeric ranges and move at runtime; the other 8 "
    "layers are shown read-only here and are edited by a human in `personaxis.md`."
)

LAYERS_HINT = (
    "Live readout of every layer in `personaxis.md`. L3 and L5 have bars (dashed mark = "
    "declared baseline, ends = walls) plus a GitHub-style diff (- before / + after) for their "
    "most recent edits. The rest are read-only summaries, tagged with who can edit them: "
    '<span class="legend-dot edit-human"></span> human approval &middot; '
    '<span class="legend-dot edit-gov"></span> governance-controlled &middot; '
    '<span class="legend-dot edit-review"></span> review required.'
)

AUDIT_HINT = (
    "`field: from -> to (tags) - reason`, from `state.json`'s `mutation_log`. "
    '<span class="legend-dot clamped"></span> clamped to a wall &middot; '
    '<span class="legend-dot blocked"></span> structurally blocked.'
)

GOV_HINT = (
    "Two real checks against the spec engine (no model needed): an identity-change attempt "
    "(blocked - no declared range) and a `mood.tone` overflow (clamped to its wall), then a "
    "reset of `mood.tone` back to baseline."
)


def build_demo() -> gr.Blocks:
    with gr.Blocks(title="Daimon", fill_height=True) as demo:
        gr.Markdown("# Daimon\n*Governed, self-evolving local AI persona - living loop*")
        gr.Markdown(INTRO)

        with gr.Row(elem_id="app-row"):
            with gr.Column(scale=10):
                gr.Markdown("## Talk to Daimon")
                chatbot = gr.Chatbot(height=480, elem_id="chat-log")
                with gr.Row():
                    msg = gr.Textbox(placeholder="Say something to Daimon...", show_label=False, scale=8)
                    send_btn = gr.Button("Send", scale=1)

            with gr.Column(scale=13):
                gr.Markdown("## State vector - 10 layers")
                gr.Markdown(LAYERS_HINT)
                layers_html = gr.HTML()

            with gr.Column(scale=10):
                gr.Markdown("## PERSONA.md - live persona")
                persona_md = gr.Markdown()

                gr.Markdown("## Audit log")
                gr.Markdown(AUDIT_HINT)
                audit_html = gr.HTML()

                gr.Markdown("## Governance demo")
                gr.Markdown(GOV_HINT)
                gov_btn = gr.Button("Run governance demo")
                gov_html = gr.HTML()

        # gr.State is the only thing passed between the two stages: the user
        # message + finished reply, so _post_process can run finish_turn()
        # without re-deriving them from `chatbot`.
        pending_msg = gr.State("")
        pending_reply = gr.State("")

        stream_inputs = [msg, chatbot]
        stream_outputs = [chatbot, msg, send_btn, pending_msg, pending_reply]
        post_outputs = [layers_html, audit_html, persona_md, msg, send_btn]

        send_btn.click(_respond, inputs=stream_inputs, outputs=stream_outputs).then(
            _post_process, inputs=[pending_msg, pending_reply], outputs=post_outputs
        )
        msg.submit(_respond, inputs=stream_inputs, outputs=stream_outputs).then(
            _post_process, inputs=[pending_msg, pending_reply], outputs=post_outputs
        )

        gov_btn.click(_run_governance_demo, outputs=[gov_html, layers_html, audit_html, persona_md])

        demo.load(_on_load, outputs=[layers_html, audit_html, persona_md])

    return demo
