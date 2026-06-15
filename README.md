# Daimon

**A governed, self-evolving AI persona that runs fully local on a small model.**

Daimon is a *daemon* (a living background process) that carries your *daimon* (your persona's
guiding spirit). Built for the Build Small Hackathon (track *Thousand Token Wood*) on top of the
open `persona.md` spec from Personaxis.

> Status: v0.1, in active build. Hackathon deadline: **2026-06-15**.
> Model: **MiniCPM5-1B (Q4_K_M, local)** - see `MASTER_CHECKLIST.md`.

---

## The idea

Agents that "self-improve" today (e.g. Hermes `SOUL.md`) edit their identity as **free text,
with no bounds and no audit**. Daimon does the opposite: a persona is a **quantitative
10-layer vector** (identity, character, personality, values, affect, cognition, memory,
metacognition, self-regulation, persona) that **evolves in real time** with your interaction,
but **inside a governed envelope**:

- every trait change is **clamped** to a declared range,
- every mutation is **logged** with its reason,
- the universal safety invariants (no consciousness claims, no identity change without
  approval, `safety >= 0.90`) **cannot be violated by construction**.

Everything runs **100% local** on a small (<= 4B) model. You watch the 10-layer state vector
move in real time, watch the governance gate **block** an unsafe change, and watch
`PERSONA.md` rewrite itself - without editing a prompt.

```
chat -> appraisal (JSON constrained by a grammar) -> deterministic mapping
     -> governance + clamp (persona.md engine) -> recompile PERSONA.md -> memory
```

The small model proposes **signals** only; the **spec engine** (`@personaxis/persona.md` CLI,
via `engine/spec_bridge.py`) enforces safety. No safety logic is duplicated in Python.

---

## Architecture

```
daimon/
  .personaxis/          our spec: project baseline + the live "daimon" persona + dev personas
  .codex/agents/         dev personas compiled to Codex subagents (TOML)
  engine/                the Living Loop (observe -> appraise -> evolve -> recompile)
  model/                 small-model serving (llama.cpp + MiniCPM GGUF)
  app/                   single gr.Blocks UI mounted on gradio.Server at "/" (Off-Brand badge)
  AGENTS.md              durable guidance for Codex/agents
  PERSONA.md             compiled behavioral baseline (this project's own persona)
  DESIGN.md              UI visual-language contract
  MASTER_CHECKLIST.md    phases F0-F6 and gates
```

---

## Run locally

```bash
# 1. serve the small model (OpenAI-compatible endpoint)
bash model/serve.sh                       # llama-server -m MiniCPM5-1B-Q4_K_M.gguf --port 8080 --jinja

# 2. run the app (single gr.Blocks UI on gradio.Server, mounted at "/")
uvicorn app.server:app --host 0.0.0.0 --port 7860
```

Open `http://localhost:7860/`. No cloud APIs required. `/api/*` (state, audit, persona,
envelopes, governance demo) is available for programmatic access without the model server.

---

## Built with Codex, using our own spec

The development plan and checklists (`MASTER_CHECKLIST.md` and the per-folder
`CHECKLIST.md` files) were written and reviewed by hand. From there, the actual code was
built **with Codex**, using MiniCPM5-1B as Codex's local model - Codex did the implementation
work, MiniCPM acted as its support model.

To give Codex a consistent persona for this, we wrote dev personas with our own
`persona.md` spec in `.personaxis/personas/dev/<slug>/` and compiled them to Codex custom
agents in `.codex/agents/<slug>.toml`. `AGENTS.md` carries the durable project rules read
automatically before any work.

| Agent | Owns |
|---|---|
| `orchestrator` | Planning, delegation, gate enforcement |
| `spec-bridge-engineer` | Python <-> spec-engine CLI bridge |
| `small-model-whisperer` | llama.cpp serving, GBNF grammar, appraisal prompt |
| `offbrand-frontend` | The `gr.Blocks` UI |
| `governance-reviewer` | Invariants, audit, the governance demo |
| `integrations-engineer` | `agents.md` + typed API endpoints |
| `deploy-engineer` | Docker build + HF Space deploy |

Codex subagents are spawned on request - either named directly, or via `orchestrator`
delegating. Commits made through Codex carry `Co-Authored-By: Codex <noreply@openai.com>`.

---

## Badges and lanes targeted

Track: **Thousand Token Wood**. Lanes: **OpenBMB (MiniCPM)** + **OpenAI Codex**.
Badges: **Tiny Titan** (<= 4B), **Off-the-Grid** (all local), **Off-Brand** (custom UI),
**Best Agent** (multi-step planning + tool use).

---

## License

The `persona.md` spec and these personas are public. See the sibling `persona.md` repo for the
spec itself.
