"""F4/F5 - Typed FastAPI routes for the Daimon Space.

Every route is a thin, typed wrapper around the living loop (engine/loop.py)
and the spec engine (engine/spec_bridge.py, engine/governance_demo.py). This
is the "Spaces as Agent Tools" surface (plan §5c): any agent with `HF_TOKEN`
can call these endpoints directly (no MCP needed), and they back the custom
Off-Brand frontend (app/frontend/) too - one living loop, multiple windows.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from engine import governance_demo, recompile
from engine.loop import SLUG, finish_turn, step, step_stream
from engine.spec_bridge import get_state

router = APIRouter(prefix="/api")


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str
    signals: dict[str, Any]
    mutations: list[dict[str, Any]]
    persona_live: str
    state: dict[str, Any]


class StateResponse(BaseModel):
    persona_id: str
    persona_version: str
    values: dict[str, float]
    mutation_log: list[dict[str, Any]]


class AuditResponse(BaseModel):
    entries: list[dict[str, Any]]


class PersonaLiveResponse(BaseModel):
    markdown: str


class EnvelopesResponse(BaseModel):
    fields: dict[str, dict[str, Any]]


class LayersResponse(BaseModel):
    layers: list[dict[str, Any]]


class GovernanceDemoResponse(BaseModel):
    identity_change: dict[str, Any]
    envelope_overflow: dict[str, Any]
    reset: dict[str, Any]


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    """Run one full living-loop turn: response -> appraisal -> mapping ->
    govern+clamp -> recompile -> memory. Requires `bash model/serve.sh`
    (MiniCPM5-1B) to be reachable - returns 503 if it is not."""
    try:
        result = step(request.message)
    except Exception as exc:  # model server unreachable, etc.
        raise HTTPException(status_code=503, detail=f"living loop unavailable: {exc}") from exc

    return ChatResponse(
        reply=result["reply"],
        signals=result["signals"],
        mutations=result["mutations"],
        persona_live=Path(result["persona_live_path"]).read_text(encoding="utf-8"),
        state=result["state"],
    )


@router.post("/chat/stream")
def chat_stream(request: ChatRequest) -> StreamingResponse:
    """Same living loop as /chat, but streamed as Server-Sent Events while the
    model generates: one `data:` line per token, tagged "thinking" (if
    TEXT_THINKING_MODE is on) or "content", then a final "done" event carrying
    the same payload as ChatResponse."""

    def events():
        try:
            for kind, payload in step_stream(request.message):
                if kind == "done":
                    result = finish_turn(request.message, payload)
                    final = {
                        "type": "done",
                        "reply": result["reply"],
                        "signals": result["signals"],
                        "mutations": result["mutations"],
                        "persona_live": Path(result["persona_live_path"]).read_text(encoding="utf-8"),
                        "state": result["state"],
                    }
                    yield f"data: {json.dumps(final)}\n\n"
                else:
                    yield f"data: {json.dumps({'type': kind, 'text': payload})}\n\n"
        except Exception as exc:  # model server unreachable, etc.
            yield f"data: {json.dumps({'type': 'error', 'detail': str(exc)})}\n\n"

    return StreamingResponse(events(), media_type="text/event-stream")


@router.get("/state", response_model=StateResponse)
def state() -> StateResponse:
    """Daimon's current state vector + full audit log (state.json, verbatim)."""
    data = get_state(SLUG)
    return StateResponse(
        persona_id=data["persona_id"],
        persona_version=data["persona_version"],
        values=data["values"],
        mutation_log=data["mutation_log"],
    )


@router.get("/audit", response_model=AuditResponse)
def audit(limit: int = 20) -> AuditResponse:
    """The most recent `limit` mutation_log entries (default 20)."""
    entries = get_state(SLUG)["mutation_log"][-limit:]
    return AuditResponse(entries=entries)


@router.get("/persona-live", response_model=PersonaLiveResponse)
def persona_live() -> PersonaLiveResponse:
    """The live PERSONA.md snippet (engine/recompile.py), re-rendered on demand
    from the current state.json - this is what "PERSONA.md rewrites itself
    live" means in F2."""
    return PersonaLiveResponse(markdown=recompile.render(SLUG))


@router.get("/envelopes", response_model=EnvelopesResponse)
def envelopes() -> EnvelopesResponse:
    """Mean + declared [min, max] range per mutable field (from personaxis.md) -
    the static "walls of the vivero" the frontend draws around each live bar."""
    return EnvelopesResponse(fields=recompile.envelopes(SLUG))


@router.get("/layers", response_model=LayersResponse)
def layers() -> LayersResponse:
    """All 10 personaxis.md layers, live: L3/L5 carry numeric fields (for the
    bars), the other 8 carry a qualitative summary + their governance edit
    policy - the full 10-layer state vector, not just the mutable slice."""
    return LayersResponse(layers=recompile.layer_summaries(SLUG))


@router.post("/governance-demo", response_model=GovernanceDemoResponse)
def run_governance_demo() -> GovernanceDemoResponse:
    """F3: induce the two real rejections (structural identity rejection +
    envelope clamp on mood.tone), then reset mood.tone back to baseline.
    Does not require the model server - it only exercises spec_bridge."""
    identity_result = governance_demo.attempt_identity_change()
    overflow_result = governance_demo.attempt_envelope_overflow()
    reset_result = governance_demo.reset_mood_tone()
    return GovernanceDemoResponse(
        identity_change=identity_result,
        envelope_overflow=overflow_result,
        reset=reset_result,
    )
