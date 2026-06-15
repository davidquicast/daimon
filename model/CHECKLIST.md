# CHECKLIST - model/ (servir el modelo pequeño)

**Objetivo:** servir MiniCPM (<= 4B, texto) como endpoint OpenAI-compatible, 100% local.

**Definition of Done:** `curl` al endpoint devuelve una completion válida; el cliente Python
apunta a él y `engine/loop.py` puede llamar `chat()` / `chat_stream()`.

## Archivos y tareas

- [x] `download_model.py` - baja `MiniCPM5-1B-Q4_K_M.gguf` de `openbmb/MiniCPM5-1B-GGUF`
      en HF y lo guarda en `model/weights/` (657 MB). Usuario confirmó: descargado.
- [x] `serve.sh` - `llama-server -m <gguf> --port 8080 -c 8192 --jinja`. `HARDWARE=auto`
      detecta GPU con `nvidia-smi`; sin GPU corre `NGL=0` (~21 tok/s con MiniCPM5-1B).
      Levantado por `app/start.sh` dentro del contenedor Docker `daimon:dev`.
- [x] `client.py` - cliente OpenAI-compatible a `http://localhost:8080/v1`:
      - `chat(messages, ...)` - respuesta completa (no streaming).
      - `chat_stream(messages, ...)` - generador que yields `("thinking"|"content"|"error", text)`;
        separa bloques `<think>...</think>` del texto visible.
      - `THINKING_MODE` (env `TEXT_THINKING_MODE=true`): habilita bloques `<think>`, sube
        `DEFAULT_MAX_TOKENS` a 4096 (vs 300 en modo normal).
      - Soporta `extra_body` para gramática GBNF (appraisal constrained decoding).
- [x] Checkpoint y quant documentados en `MASTER_CHECKLIST.md` (sección Metadatos).

## Notas
- `--jinja` habilita la plantilla de chat nativa de MiniCPM.
- Multimodales opcionales (V-4.6, o-4.5, VoxCPM2) y proveedor `hf_inference` documentados
  en `.env.example`; no implementados en este ciclo.

**Gate asociado:** G0.
