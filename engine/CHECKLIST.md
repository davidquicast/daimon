# CHECKLIST - engine/ (el Living Loop)

**Objetivo:** orquestar el lazo vivo gobernado. El modelo pequeño propone señales; el motor
del spec impone la seguridad. Cero duplicación de la lógica del spec (eso vive en el CLI).

**Definition of Done:** 5 turnos de chat mueven el vector de forma estable, clampeada y
registrada, y `PERSONA.md` se recompila tras cada turno.

## Archivos y tareas

- [x] `loop.py` - orquesta los 6 pasos. Funciones principales:
      - `build_messages(user_message, history)`: construye el prompt con `PERSONA.md`
        recompilado como system prompt + hasta `MAX_HISTORY_TURNS=8` pares previos de
        `gr.Chatbot` (salta entradas con `metadata` — thinking bubbles).
      - `step_stream(user_message, history)`: generador, yields `("thinking"|"content", text)`
        chunks + `("done", reply_text)` final. **No** corre los pasos 2-6.
      - `finish_turn(user_message, reply)`: pasos 2-6 (appraise -> map -> mutate/clamp ->
        recompile -> curate_memory). Llamado por la UI/API **después** de que el stream
        termina (para no bloquear el chat).
      - `step(user_message, history)`: no-streaming, llama `finish_turn` internamente.
      - `__main__` corre los 5 turnos de demo (Gate G2) manteniendo `history` propio.
- [x] `appraise.py` - paso 2: prompt de evaluación + decodificación restringida (GBNF, `extra_body={"grammar": ...}` vía `model/client.chat`). Salida: JSON de 6 campos (`sentiment`, `engagement`, `correction`, `target`, `direction`, `reason`), con fallback neutral si no parsea.
- [x] `grammars/appraisal.gbnf` - gramática que fuerza el JSON de 6 campos con valores cuantizados (sentiment/engagement en pasos de 0.5/0.25, enums para target/direction) para que un modelo de 1B la cumpla con fiabilidad.
- [x] `mapping.py` - paso 3: tabla determinista señal -> delta sobre `state.json` (`sentiment`->`mood.tone`+`affect.valence`, `engagement`->`traits.extraversion`+`traits.openness`, `correction`+`target`+`direction`->trait corregido). Cada regla documentada con su escala y tope (0.03-0.08).
- [x] `spec_bridge.py` - pasos 4 y 5 (bridge): subprocess al CLI `@personaxis/persona.md` (`state mutate`, `validate`, `compile`). Hecho en F1; en esta fase se corrigió `get_compiled_prompt` (regex de `developer_instructions` fallaba con el bloque `[[skills.config]]` al final del `.toml`).
- [x] `memory.py` (v4) - paso 6, memoria curada únicamente (no hay copia cruda del
      chat - el historial vive solo en `gr.Chatbot`, ver `build_messages`):
      `memory.md` (cross-session) + `memory/<YYYY-MM-DD>.md` (resumen
      consolidado de la sesión, frontmatter + episodic/user_preferences/
      procedural/autobiographical) - que `curate_memory()` reescribe con el
      modelo local tras cada turno, formato alineado con
      `persona.md/.personaxis/personas/cmo/`.
- [x] `recompile.py` - paso 5: re-renderiza `.personaxis/personas/<slug>/PERSONA.md` desde
      `personaxis.md` + `policy.yaml` + `state.json`, sin LLM. `PERSONA.md` ES el system
      prompt (`engine/loop.py:build_messages`). Sigue el contrato de secciones v0.7.0
      (`PERSONA_template.md`): Identity & Purpose, Character, Personality & Voice, Values,
      How You Think, Limits, Self-Improvement (con subsecciones de estado vivo: traits,
      affect/mood y mutation_log), Resources. Sin secciones top-level inventadas. Cabecera
      HTML-comment de procedencia invisible al renderizar.

## Notas de diseño
- El appraisal debe ser MINIMO para que un <= 4B lo cumpla con fiabilidad. Por eso los campos numéricos están cuantizados (no floats libres) en `appraisal.gbnf`.
- Nunca dejar que el modelo escriba directo en `state.json`: siempre pasar por `state mutate` (`spec_bridge.mutate`).
- Estabilidad: cada regla de `mapping.py` tiene un delta máximo de 0.03-0.08 por turno; combinado con el clamp a envelope del CLI, evita runaway.
- **"Recompile" reinterpretado para F2**: `personaxis compile` (agente-provider, requiere un documento completo escrito a mano/por LLM) es demasiado pesado para correr cada turno. `recompile.py` hace un recompile barato y determinista (sin LLM) de `PERSONA.md`, que es lo que el frontend (F4) muestra latiendo y lo que `loop.py` usa como system prompt.

## Investigación a ampliar
- Constrained decoding GBNF / json-schema en llama.cpp.
- Reflexion / SEAL / EvolveMem para el diseño del appraisal y la consolidación de memoria.

**Gate asociado:** G2 (loop) y aporta a G1 (bridge) y G3 (governance).

## Estado de Gate G2
Código completo y probado en frío (sin LLM): `mapping.signals_to_deltas`, `memory.curate_memory`,
`recompile.render/write`, `spec_bridge.get_compiled_prompt` verificados con Python.
El chat UI probado en navegador end-to-end (streaming, thinking bubble, mutaciones en
`state.json` post-turno). **Pendiente solo**: correr `python -m engine.loop` con
`model/serve.sh` activo para el smoke test formal de 5 turnos sin UI.
