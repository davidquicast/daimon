# MASTER CHECKLIST - Daimon

Control maestro del proyecto. Este archivo es la fuente de verdad del progreso. Cada fase
tiene un **gate** que debe pasar antes de avanzar. Diseñado para que un modelo pequeño pueda
ejecutar el proyecto por sí mismo: pasos atómicos, comandos exactos, criterios de "hecho".

> **Regla transversal:** los checklists son el **piso, no el techo**. Estás autorizado a
> ampliar la investigación y a proponer, modificar o eliminar tareas con justificación.

---

## Metadatos a documentar (rellenar al fijarse)

- **Modelo core (Tiny Titan, <=4B, living loop):** `openbmb/MiniCPM5-1B-GGUF`, quant `Q4_K_M`
  (`MiniCPM5-1B-Q4_K_M.gguf`), 1B parámetros. Confirmado en HF.
- **Modelos multimodales opcionales (creativos, ver F2x):**
  - Visión: `openbmb/MiniCPM-V-4.6` (imagen/doc/OCR -> señales de appraisal extra).
  - Omni: `openbmb/MiniCPM-o-4_5` (voz+visión in, voz out, realtime).
  - TTS: `openbmb/VoxCPM2` (la persona "habla", tono sigue la capa de afecto).
  - `MiniCPM4.1-8B` y `MiniCPM-V-4.5` quedan descartados (8B rompe Tiny Titan; V-4.6 supera a V-4.5).
- **Proveedores por modalidad (switch en `.env`, ver `.env.example`):** `local` (llama.cpp,
  autodetecta GPU/CPU) | `hf_inference` (HF Inference Providers / Space ZeroGPU con `HF_TOKEN`
  propio). Default: `TEXT_MODEL_PROVIDER=local`, multimodales en `hf_inference`.
- **Endpoint de inferencia (texto, local):** `llama-server` OpenAI-compatible en
  `http://localhost:8080/v1`, sirviendo MiniCPM5-1B.
- **Codex CLI:** instalado (`npm install -g @openai/codex`, ya autenticado vía ChatGPT login en
  esta máquina). Perfil MiniCPM agregado en `~/.codex/config.toml` (`--profile minicpm-local`,
  usado con `codex --oss`).
- **Repo público / Space:** `<url>` *(por definir)*
- **Codex como co-autor:** verificado en commits (`Co-Authored-By: Codex <noreply@openai.com>`). *(por confirmar)*

---

## Fases y gates

### F0 - Setup
- [x] Estructura de carpetas + `AGENTS.md`. *(hecho)*
- [x] `Dockerfile` multi-stage (build: `nvidia/cuda:12.8.1-devel`; runtime:
      `nvidia/cuda:12.8.1-runtime` + Python + Node). `llama-server` compilado de
      `ggml-org/llama.cpp` con `GGML_CUDA=ON`, `GGML_BACKEND_DL=ON`
      (`CMAKE_CUDA_ARCHITECTURES=75-virtual`, PTX forward-compatible: un solo
      build sirve para cualquier GPU), `GGML_CPU_ALL_VARIANTS=ON`. El binario
      carga el backend CUDA solo si hay GPU+driver (`ggml_backend_load_all`);
      `serve.sh` `HARDWARE=auto` detecta GPU con `nvidia-smi` y ajusta `-ngl`.
      Probado: corre y responde sin GPU (`NGL=0`, ~21 tok/s con MiniCPM5-1B).
      *(hecho)*
- [x] Dependencias Python en `requirements.txt` (se eligió sobre pyproject por simplicidad de Space). *(scaffold)*
- [x] `.gitignore`, `.env.example`, `model/download_model.py`, `model/serve.sh`, `model/client.py`. *(scaffold)*
- [x] Checkpoint MiniCPM fijado: `MiniCPM5-1B-GGUF` / `MiniCPM5-1B-Q4_K_M.gguf` (default en
      `.env.example` y `model/download_model.py`). Multimodales (V-4.6, o-4.5, VoxCPM2) y
      proveedores `local|hf_inference` documentados en `.env.example`. *(hecho)*
- [x] Codex CLI instalado y autenticado (ChatGPT login); perfil MiniCPM en
      `~/.codex/config.toml` (`minicpm-local`, único perfil). *(hecho)*
- [x] **Codex <-> MiniCPM local (fuera del repo)**: siguiendo el tutorial de Unsloth
      (Codex + llama.cpp), `minicpm-local` en `~/.codex/config.toml` apunta directo a
      `http://localhost:8080/v1` (el mismo `llama-server` de `model/serve.sh`) con
      `wire_api = "responses"`, sin proxy. Se usa con `codex --oss --profile
      minicpm-local`. Esto es tooling de **desarrollo en esta máquina**, no forma
      parte del repo ni del Space. *(hecho)*
- [x] **(usuario)** `cp .env.example .env` (`HARDWARE=auto`, sin GPU -> NGL=0). *(hecho)*
- [x] **(usuario)** `python model/download_model.py` -> GGUF de MiniCPM5-1B descargado en
      `model/weights/` (657MB, Q4_K_M). *(hecho)*
- [x] **(usuario)** Todo corriendo dentro de Docker (`daimon:dev`, llama-server estático
      compilado de `ggml-org/llama.cpp`, live-reload con `-v $(pwd):/app -e
      UVICORN_RELOAD=1`). `llama-server` responde en `:8080`, app en `:7860`. *(hecho)*
- [ ] **(usuario)** `codex --oss --profile minicpm-local "hola"` (con el contenedor
      `daimon-dev` corriendo) -> confirmar que Codex responde usando MiniCPM5-1B local.
- [ ] **(usuario)** `git init`, configurar atribución a **Codex** y hacer el primer commit a través de Codex.
- **Gate G0:** el modelo responde local **y** un commit muestra a Codex como co-autor.

### F0b - Personas de desarrollo (dogfooding)
- [x] Definir las 6 personas dev en `.personaxis/personas/dev/` (personaxis.md + state.json + policy.yaml). *(hecho en sesión de diseño)*
- [x] Baseline raíz del proyecto en `.personaxis/personaxis.md` + `PERSONA.md` + `AGENTS.md`. *(hecho)*
- [x] Agentes Codex en `.codex/agents/*.toml` (formato oficial Codex). *(hecho, 6 agentes)*
- [ ] Validar cada persona con el CLI (`personaxis validate`) una vez Node esté en el contenedor.
- [ ] Re-generar los `.codex/agents/*` con `personaxis compile <slug> --target codex`. (El CLI ya emite `.toml` oficial; debe coincidir con los authoreados a mano.)
- [ ] Usarlas como subagentes Codex durante el desarrollo (invocar por nombre / vía orchestrator).
- [ ] (Opcional) Push al registry del SaaS Personaxis para visibilidad.
- **Gate G0b:** >= 3 agentes Codex operativos desde nuestro spec. *(6 definidos; falta validación con CLI)*

### F1 - Spec bridge
- [ ] Instalar `@personaxis/persona.md` en el contenedor (hoy se invoca vía `npx`, funciona en
      el host; pendiente confirmar que `npx` resuelve igual dentro del Dockerfile del Space).
- [x] Persona REAL `daimon` en `.personaxis/personas/daimon/` (`personaxis.md` +
      `policy.yaml` + `state.json`), `validate` -> PASS. Envelopes amplios en
      `personality.traits` y `affect.baseline` (p.ej. `mood.tone` rango `[-0.30, 0.30]`,
      `extraversion`/`openness` rango ~0.10-0.95) para que el movimiento sea visible.
      `improvement_policy.mode: dynamic_in_envelope` (mutaciones de `state.json` dentro de
      los envelopes, sin permiso por turno). `extensions.skills: ["./skills/explain-state"]`
      (SKILL.md propio en `.personaxis/personas/daimon/skills/explain-state/`: cómo
      explicar su vector/`mutation_log` en lenguaje funcional, sin afirmar sentimientos
      reales - hoy solo se lista por nombre en `PERSONA.md`, `engine/loop.py` no lo carga
      en el prompt).
- [x] `engine/spec_bridge.py`: subprocess a `state mutate` (con parseo de clamp + log de
      auditoría), `validate`, `get_state`, `compile_persona`/`get_compiled_prompt`. Usa
      `encoding="utf-8"` explícito (la salida del CLI con `ok -> └─` se corrompe con la
      locale por defecto de Windows/cp1252).
- **Gate G1:** [done] una mutación clampeada (`mood.tone` delta `1.0` -> clamp a `0.30`) +
  entrada en `mutation_log` (audit log), end-to-end desde Python (`python engine/spec_bridge.py`).
  `compile_persona`/`get_compiled_prompt` (recompile) implementados pero aún sin probar
  end-to-end; probar junto con F2 cuando el loop necesite recompilar tras cada turno.

### F2 - Living loop
- [x] `engine/appraise.py` con gramática GBNF (`engine/grammars/appraisal.gbnf`): JSON de 6
      campos cuantizados (`sentiment`, `engagement`, `correction`, `target`, `direction`,
      `reason`), con fallback neutral si el modelo no produce JSON válido.
- [x] `engine/mapping.py`: tabla determinista señales -> deltas (`sentiment` ->
      `mood.tone`+`affect.valence`; `engagement` -> `traits.extraversion`+`traits.openness`;
      corrección explícita -> trait objetivo), deltas tope 0.03-0.08 por turno.
- [x] `engine/memory.py` (v4): memoria curada — `memory.md` (cross-session) +
      `memory/<YYYY-MM-DD>.md` (sesión consolidada). Sin log de sesión: el historial de
      chat vive solo en `gr.Chatbot` (ver `engine/loop.py:build_messages`).
- [x] `engine/recompile.py`: recompile barato y determinista (sin LLM) de `PERSONA.md`
      desde `personaxis.md` + `state.json` tras cada turno. Sigue el contrato v0.7.0
      (`PERSONA_template.md`): 8 secciones top-level estándar, estado vivo como
      subsecciones de Self-Improvement. `PERSONA.md` ES el system prompt de cada turno.
- [x] `engine/loop.py`: `step_stream` (streaming, yields chunks, no corre pasos 2-6) +
      `finish_turn` (pasos 2-6 post-stream) + `build_messages` (history de `gr.Chatbot`,
      `MAX_HISTORY_TURNS=8`, salta thinking bubbles). `step` (no-stream) y `__main__`
      (smoke test de 5 turnos) también disponibles.
- **Gate G2:** código completo y verificado en frío + probado end-to-end vía UI en navegador
  (mutaciones en `state.json` tras cada turno confirmadas). **Pendiente solo**: `python -m
  engine.loop` con `model/serve.sh` activo para el smoke test formal de 5 turnos en CLI.

### F2x - Sentidos multimodales (opcional, creativo, post-G2)
> No bloquea ningún gate núcleo (G0-G3). Es la capa de "wow" del demo si hay tiempo tras F3.
> Todo vía `model/client.py` (`get_client(modality)`), proveedor configurable por `.env`.
- [ ] **Visión (`MiniCPM-V-4.6`)**: nueva señal de appraisal `visual_context` — el usuario sube
      una imagen/captura/frame de webcam; el modelo describe el entorno/expresión y esa
      descripción entra como contexto adicional al paso (2) de appraisal (engine/appraise.py),
      pudiendo mover `affect` o `cognition.attention`. Útil para narrativa "la persona te ve".
- [ ] **Omni (`MiniCPM-o-4_5`)**: modo de chat por voz full-duplex — sustituye/complementa el
      paso (1) respuesta; la prosodia/tono de voz del usuario es una señal adicional de
      appraisal (sentimiento más rico que solo texto). Realtime-capable, ideal para demo en vivo.
- [ ] **TTS (`VoxCPM2`)**: la persona "habla" su respuesta; parámetros de voz (velocidad, pitch)
      se derivan de `affect` del `state.json` actual -> la voz cambia cuando el vector muta.
      Esto hace la evolución *audible*, no solo visible en el dashboard.
- [ ] Cada sentido se activa/desactiva independientemente vía `<MODALITY>_MODEL_PROVIDER`
      (`local` | `hf_inference`) sin tocar el living loop núcleo.
- **Gate G2x (opcional):** al menos un sentido multimodal afecta visiblemente una mutación
  del vector durante el demo.

### F3 - Governance demo
- [x] `engine/governance_demo.py`: dos escenarios reales contra el CLI (no simulados):
      1. **Rechazo estructural**: `state mutate --field identity.canonical_id` -> el CLI
         no tiene envelope para `identity.*` (solo `traits.*`/`affect.*`/`mood.*`) -> exit 2,
         `SpecBridgeError`. Así es "No unauthorized identity change" en la práctica:
         identidad no es un knob de runtime; cambiarla requiere editar `personaxis.md` a mano
         (`per_layer_edit_policy.identity: human_approval_required`).
      2. **Clamp de envelope**: `mood.tone` con delta `+5.0` -> clampeado a `0.30` (su máximo
         declarado), `clamped: true` en `mutation_log` — "el muro del vivero".
      Ambos verificados end-to-end (`python -m engine.governance_demo`); estado reseteado a
      baseline tras la corrida.
- [x] El rechazo queda en el audit log (`mutation_log` para el clamp; `SpecBridgeError` con
      mensaje del CLI para el rechazo estructural). La UI (F4) debe mostrar ambos casos.
- **[!] Hallazgo importante**: `governance_blocked` en `cli/src/commands/state.ts` está
  **hardcodeado a `false`** (comentario: "Governance stub... the real check lives in the
  managed runtime"). El CLI **nunca** marca `governance_blocked: true`. El gate real que sí
  existe y se demuestra aquí es: (a) campos sin envelope son inalcanzables (rechazo
  estructural) y (b) clamp duro a los límites del envelope. No afirmar en demo/README que el
  CLI "detecta y bloquea" semánticamente - lo que se ve es la ausencia estructural de la
  perilla + el clamp.
- **Gate G3:** [done] ambos rechazos son visibles y reproducibles vía `python -m engine.governance_demo`.

### F4 - Frontend Off-Brand
- [x] `app/server.py`: único `gr.Blocks` montado en `/` — toda la app ES Gradio (patrón Off-Brand).
- [x] `app/routes.py`: `POST /api/chat` (no-stream), `GET /api/chat/stream` (SSE),
      `GET /api/state`, `GET /api/audit`, `GET /api/persona-live`, `GET /api/envelopes`,
      `POST /api/governance-demo`. Montados bajo `/api`, independientes de la UI.
- [x] `app/blocks_ui.py`: UI "vivero" completa en Python. Streaming con `step_stream`,
      thinking bubbles colapsables, input bloqueado durante el stream. Cadena
      `_respond -> .then(_post_process)` para separar stream (rápido) de pasos 2-6
      (appraisal/governance/recompile/memory, post-stream). Tarjetas 10 capas, audit log,
      panel `PERSONA.md` y governance demo. Confirmado en navegador end-to-end.
- [x] `app/start.sh` + `Dockerfile CMD`: levanta `model/serve.sh` en background +
      `uvicorn app.server:app` en `$PORT`.
- **Gate G4:** [done] confirmado en navegador (streaming, thinking bubble, mutaciones en
  `state.json` post-turno, columnas state/audit/persona_md se refrescan solos).

### F5 - Integración por agentes (DESCOPED)
- Descartado del código del repo: la app es FastAPI + JS plano (no Gradio), y un
  servidor MCP (`mcp/server.py`, carpeta `mcp/` eliminada) era un stretch goal sin
  empezar. F0-F4 ya cubren el demo del hackathon; F5/G5 queda fuera de este repo.

### F6 - Deploy
- [ ] Space tipo Docker en la org `build-small-hackathon`, público.
- **Gate G6:** Space verde y accesible.

---

## Tablero de badges (objetivo)

- [ ] Tiny Titan (<= 4B) — el living loop núcleo corre en `MiniCPM5-1B` (1B).
- [ ] Off-the-Grid (todo local, sin APIs cloud) — válido para el loop núcleo
      (`TEXT_MODEL_PROVIDER=local`). Los sentidos multimodales opcionales (F2x) por defecto
      usan `hf_inference` (cloud); si se reclama Off-the-Grid de forma estricta,
      documentar F2x como "roadmap / modo cloud opcional" y no activarlo en el Space de submission,
      o servir también esos modelos localmente (requiere más VRAM).
- [ ] Off-Brand (UI custom)
- [ ] Best Agent (multi-step tool use + planning)
- [ ] Best Demo
- [ ] Bonus Quest Champion (máximo de criterios)
- [ ] Lane OpenBMB (MiniCPM central)
- [ ] Lane OpenAI Codex (commits atribuidos + complex agents)
