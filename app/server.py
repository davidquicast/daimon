"""F4 - Entry point for the Daimon Space.

ONE gr.Blocks app (app/blocks_ui.py), mounted at "/" via
gr.mount_gradio_app - the chat, the 10-layer state vector, PERSONA.md, the
audit log and the governance demo (F3) are all Gradio components in a single
custom-themed Blocks layout (the Off-Brand "custom UI on gr.Server" pattern),
backed by the same living loop (engine/loop.py). The typed FastAPI routes in
app/routes.py stay mounted under /api for programmatic/agent access
("Spaces as Agent Tools", plan §5c).

Run with:
    uvicorn app.server:app --host 0.0.0.0 --port 7860
(requires `bash model/serve.sh` running separately for chat to work; the
state vector, audit log and governance demo work without the model server.)
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import gradio as gr
from fastapi import FastAPI

from app.blocks_ui import CUSTOM_CSS, build_demo
from app.routes import router

app = FastAPI(title="Daimon")
app.include_router(router)

demo = build_demo()
app = gr.mount_gradio_app(app, demo, path="/", css=CUSTOM_CSS)
