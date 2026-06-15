# CHECKLIST - app/ (frontend Off-Brand: un solo gr.Blocks)

**Objetivo:** UI del "cerebro-vivero" de 10 capas como un único `gr.Blocks` app, en vivo
(streaming). Cubre el badge Off-Brand y la narrativa Thousand Token Wood - "toda la app
es la app Gradio", sin frontend estático ni superficie `/gradio` separada.

**Definition of Done:** en el navegador, el vector de 10 capas late en tiempo real; se ven
las mutaciones, el audit log y el rechazo del governance gate; `PERSONA.md` se actualiza solo.

## Archivos y tareas

- [x] `server.py` - `FastAPI` con UNA sola superficie de UI: `app/blocks_ui.py` (`gr.Blocks`)
      montado en `/` vía `gr.mount_gradio_app(app, demo, path="/", css=CUSTOM_CSS)`. Los
      endpoints FastAPI tipados de `routes.py` siguen bajo `/api` para "Spaces as Agent
      Tools" (F5). No hay `/gradio` separado ni frontend estático en `app/frontend/`.
- [x] `routes.py` - endpoints tipados con Pydantic:
      - `POST /api/chat` (no-stream, `engine.loop.step`, 503 si el model server no responde)
      - `GET /api/chat/stream` (SSE, `step_stream` + `finish_turn` tras el último chunk)
      - `GET /api/state`, `GET /api/audit`, `GET /api/persona-live`
      - `GET /api/envelopes` (mean+range por campo, `engine/recompile.py:envelopes()`)
      - `POST /api/governance-demo` (corre los 2 escenarios de F3 + reset)
- [x] `blocks_ui.py` (reemplaza `frontend/index.html`+`brain.js`+`styles.css`, todo en Python):
      - `CUSTOM_CSS` (tema oscuro "vivero"), `gr.Chatbot` con streaming vía `step_stream`.
      - Thinking bubbles colapsables (`metadata: {title, status: "pending"|"done"}`) por turno.
      - Input y botón bloqueados (`interactive=False`) mientras el stream está activo.
      - Cadena `.click/.submit -> _respond -> .then(_post_process)`: `_respond` hace el stream
        y pasa `(pending_msg, pending_reply)` vía `gr.State`; `_post_process` corre
        `finish_turn` (pasos 2-6) y refresca columnas (layers, audit, persona_md) solo
        después de que el modelo termina de responder.
      - Tarjetas 10 capas con barras `[min..max]` + baseline + diffs estilo GitHub.
      - Panel `PERSONA.md` (`gr.Markdown`), audit log (`gr.HTML`) y botón governance demo.

## Notas de diseño
- Mostrar explícitamente: rasgo actual vs su envelope (min, max) y la razón de cada mutación. -> hecho (bars + audit log con `reason`).
- El rechazo del gate debe ser visualmente evidente (es el diferenciador vs Hermes). -> hecho (panel de governance demo con tarjetas dedicadas).
- Off-Brand exige que la app misma sea Gradio, no un widget decorativo aparte: un único
  `gr.Blocks` con CSS custom satisface esto sin perder la estética "vivero". El chat usa
  streaming real (generador `step_stream` -> `gr.Chatbot`), no polling.
- `requirements.txt`: se añadieron `fastapi`/`uvicorn` explícitos (antes solo transitivos vía gradio).

## Verificación
- Cold (sin model server): `/api/state`, `/api/audit`, `/api/persona-live`, `/api/envelopes`,
  `/api/governance-demo` funcionan; `_on_load` carga el layout completo.
- Con model server activo + navegador: streaming de chat confirmado (thinking bubble aparece,
  se colapsa al terminar, input se bloquea/desbloquea, columnas state/audit/persona_md
  se refrescan post-turno, mutaciones aparecen en `state.json`). Probado end-to-end.

## Cómo correr
```bash
uvicorn app.server:app --host 0.0.0.0 --port 7860
```
Abrir `http://localhost:7860/` - toda la app (chat, vector de 10 capas, PERSONA.md, audit
log, governance demo) vive ahí, como un único `gr.Blocks`. `/api/*` sigue disponible para
acceso programático. El chat requiere `bash model/serve.sh` activo aparte; el resto de
paneles funciona sin el model server.

## Investigación a ampliar
- Spaces as Agent Tools: cómo se genera el `agents.md` a partir de los endpoints FastAPI
  de `app/routes.py` (F5) - confirmar si FastAPI custom routes (no Gradio) entran en ese
  `agents.md` o si hace falta documentarlos a mano.

**Gate G4:** [done] confirmado en navegador (streaming, thinking bubble, state mutations, governance demo visible).

**Gate asociado:** G4 (frontend), aporta a G3 (governance visible).
