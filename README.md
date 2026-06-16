---
title: Daimon
colorFrom: yellow
colorTo: indigo
sdk: docker
app_port: 7860
pinned: true
license: mit
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

[![GitHub](https://img.shields.io/badge/GitHub-davidquicast%2Fdaimon-black?logo=github)](https://github.com/davidquicast/daimon)  [![🤗 Space](https://img.shields.io/badge/🤗%20Space-davidquicast%2Fdaimon-FFD21E)](https://huggingface.co/spaces/davidquicast/daimon)  [![🤗 Hackathon](https://img.shields.io/badge/🤗%20Build%20Small-Hackathon-blue)](https://huggingface.co/spaces/build-small-hackathon/daimon)

**A governed, self-evolving AI persona that runs fully local on a small model.**

> Can SLMs become a dedicated persona layer for AI apps? Rather than static prompts, Daimon explores whether persona state, evolution, and constraints can operate independently, while other models focus on reasoning and tasks.

Daimon is an experimental implementation of the [personaxis](https://github.com/personaxis/persona.md) 10-layer persona architecture, running on **MiniCPM5-1B-Q4_K_M via llama.cpp**, under 1B parameters, no cloud.

Every message, MiniCPM appraises the conversation and proposes small changes to its personality and mood. A governance gate clamps, audits, or rejects each change live. You watch the vector move, `PERSONA.md` rewrite itself, and the model refuse to touch its own identity.

```
chat -> appraisal (JSON constrained by grammar) -> deterministic mapping
     -> governance + clamp -> recompile PERSONA.md -> memory
```

### How the persona works

`personaxis.md` is the **architecture spec**: a structured definition of the persona across 10 governed layers. It declares who Daimon is, what it values, how it reasons, and what it cannot change about itself.

`PERSONA.md` is the **live system prompt**: compiled from that spec after every interaction. It is what the model actually reads. When the governance engine accepts a change, it rewrites `PERSONA.md` so the next message already talks to a slightly different Daimon.

**The 10 personaxis layers:**
1. Identity
2. Character
3. Personality
4. Values & Drives
5. Affect
6. Cognition
7. Memory
8. Metacognition
9. Reflexive Self-Regulation
10. Persona

---

## Demo

<video src="https://media.githubusercontent.com/media/davidquicast/daimon/main/assets/demo.mp4" controls width="100%"></video>

> Posted on X: [x.com/davidquicast/status/2066722575577706745](https://x.com/davidquicast/status/2066722575577706745)

---

## Architecture

```
.personaxis/     spec: project baseline + live "daimon" persona
engine/          living loop (appraise → map → govern → recompile → memory)
model/           small-model serving (llama.cpp + MiniCPM GGUF)
app/             single gr.Blocks UI at "/"
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

MIT. The specification belongs to the community. Personaxis builds the tooling and platform around it.

See [personaxis/persona.md](https://github.com/personaxis/persona.md) for the spec.
