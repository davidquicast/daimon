# CHECKLIST - .personaxis/ (nuestro spec en acción)

**Objetivo:** definir, con el spec de 10 capas, tanto la persona REAL que el usuario ve
evolucionar en el Space como las personas de **desarrollo** (dogfooding) que construyen el
proyecto y se compilan a agentes Codex.

**Definition of Done:** todas las personas validan con el CLI; las dev compilan a
`.codex/agents/*.toml` y operan como subagentes Codex.

## Persona en vivo (real, no demo)
- [ ] `personas/<slug>/` (una persona REAL de uso, no un demo) con `personaxis.md` + `state.json`
  + `policy.yaml`. Envelopes amplios para que el movimiento del vector sea visible. El Space
  evoluciona esta persona en vivo; todo es real.

## Personas de desarrollo (set inicial, AMPLIABLE)
Basado en patrones 2026 (Planner -> Architect -> Implementer -> Tester -> Reviewer). Cada una
en `personas/dev/<slug>/` con su `personaxis.md`.

- [ ] `orchestrator` - descompone el MASTER_CHECKLIST, delega, mantiene foco y gates. Énfasis: cognición (planning), metacognición, baja verbosidad.
- [ ] `spec-bridge-engineer` - integración Python <-> CLI TS; prohíbe duplicar lógica del spec. Énfasis: rigor/conciencia alto.
- [ ] `small-model-whisperer` - constrained decoding (GBNF), prompts de appraisal, serving llama.cpp. Énfasis: apertura/experimentación, evidence-first.
- [ ] `offbrand-frontend` - `gr.Server` + UI custom del cerebro-vivero. Énfasis: apertura alta, afecto expresivo controlado, voz lúdica.
- [ ] `governance-reviewer` - vela invariantes, audita mutaciones, revisa seguridad/drift. Énfasis: honesty=hard, safety>=0.90, refusals categóricos.
- [ ] `integrations-engineer` - `agents.md` + endpoints tipados + interop Claude Code/Codex/Hermes. Énfasis: cognición sistémica, estándares.
- [ ] `deploy-engineer` - build Docker reproducible + deploy HF Space, offline-capable. Énfasis: reproducibilidad, frugalidad, sin secretos en la imagen.

## Compilación y registro
- [ ] Validar cada persona (`personaxis validate`).
- [ ] Compilar a Codex (`personaxis` target codex) -> `.codex/agents/*.toml`.
- [ ] `AGENTS.md` del repo con guía durable para Codex.
- [ ] (Opcional) Push de las personas al registry del SaaS Personaxis (visibilidad).

## Nota de alcance (no limitar)
Investigar más roles (Researcher, QA/Tester, DevOps, Observability, Security) y proponer,
fusionar o eliminar personas según lo que el proyecto realmente necesite, con justificación.
No es una lista cerrada.

**Gate asociado:** G0b. Usa el spec canónico de `../persona.md` como fuente de verdad.
