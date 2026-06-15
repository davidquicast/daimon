---
title: Daimon
colorFrom: yellow
colorTo: indigo
sdk: docker
app_port: 7860
pinned: true
license: apache-2.0
short_description: Governed self-evolving AI persona, fully local on a SLM.
tags:
  - build-small-hackathon
  - track:wood
  - lane:openbmb
  - lane:codex
  - achievement:tiny-titan
  - achievement:offgrid
  - achievement:off-brand
  - achievement:best-agent
---

# Daimon

**A governed, self-evolving AI persona that runs fully local on a small model.**

For this hackathon, Daimon hands its own `personaxis.md` to **MiniCPM5-1B, running fully
local through llama.cpp** - under 1B parameters, no cloud. Every message, MiniCPM appraises
the conversation and proposes small changes to its own personality and mood, and a
governance gate clamps, audits, or rejects each one live. You watch the 10-layer vector
move, watch `PERSONA.md` rewrite itself, and watch it refuse to touch its own identity.

```
chat -> appraisal (JSON constrained by grammar) -> deterministic mapping
     -> governance + clamp -> recompile PERSONA.md -> memory
```

Track: **Thousand Token Wood**. Lanes: **OpenBMB (MiniCPM)** + **OpenAI Codex**.
Badges: **Tiny Titan** (<= 4B), **Off-the-Grid** (all local), **Off-Brand** (custom UI), **Best Agent**.

---

## Architecture

```
.personaxis/     spec: project baseline + live "daimon" persona
engine/          living loop (appraise -> map -> govern -> recompile -> memory)
model/           small-model serving (llama.cpp + MiniCPM GGUF)
app/             single gr.Blocks UI at "/" (Off-Brand)
AGENTS.md        project guidance
PERSONA.md       compiled behavioral baseline
```

---

## Run locally

```bash
# serve the model
bash model/serve.sh

# run the app
uvicorn app.server:app --host 0.0.0.0 --port 7860
```

Open `http://localhost:7860/`. No cloud APIs required.
`/api/*` (state, audit, persona, envelopes, governance demo) works without the model server.

---

## License

The `persona.md` spec and these personas are public. See the sibling `persona.md` repo for the spec itself.
