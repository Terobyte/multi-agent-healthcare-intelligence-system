"""FastAPI route registrar for the sponsor stack.

Single entry point :func:`register` that ``app.main`` calls once after the
``FastAPI`` app and ``slowapi.Limiter`` are constructed. Each route is mounted
only when its env flag is true, and every public route is gated by
``Depends(require_demo_key)`` (bug #1 doctrine).
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, ConfigDict, Field
from slowapi import Limiter

from app.sponsor.flags import flags


logger = logging.getLogger(__name__)


class _SponsorTriageRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    symptoms: str = Field(max_length=2000)
    language: str = Field(default="en", max_length=8)


class _SponsorGenieRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    query: str = Field(max_length=500)
    conversation_id: str | None = Field(default=None, max_length=128)


class _SponsorNarrateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    demo_id: str = Field(max_length=8)
    lang: str = Field(default="hi", max_length=4)
    hospital_name: str = Field(default="", max_length=120)
    eta_min: int = Field(default=0, ge=0, le=120)


def register(app: FastAPI, limiter: Limiter, require_demo_key: Any) -> None:
    """Mount /sponsor/* routes. Idempotent across reloads."""

    @app.get("/sponsor/health")
    async def sponsor_health() -> dict[str, Any]:
        # Frontend reads this to render the «demo mode» banner. No auth: it
        # exposes only flag state, no secrets, no warehouse data.
        return {
            "safe_demo": flags.SAFE_DEMO,
            "agent_bricks": flags.SPONSOR_AGENT_BRICKS,
            "genie": flags.SPONSOR_GENIE,
            "genie_live": flags.SPONSOR_GENIE_LIVE,
            "voice": flags.SPONSOR_VOICE,
            "ka": flags.SPONSOR_KA,
        }

    @app.post(
        "/sponsor/triage",
        dependencies=[Depends(require_demo_key)],
    )
    @limiter.limit("120/minute")
    async def sponsor_triage(
        request: Request, body: _SponsorTriageRequest
    ) -> JSONResponse:
        if not flags.SPONSOR_AGENT_BRICKS:
            raise HTTPException(status_code=404, detail="sponsor_agent_bricks_disabled")

        from app.sponsor.agent_bricks import run_triage

        result = run_triage(body.symptoms, body.language)
        return JSONResponse(
            content={
                "agent": "mosaic_ai_agent_framework",
                "model": "responses_agent",
                "output": result.model_dump(),
            }
        )

    @app.post(
        "/sponsor/genie/query",
        dependencies=[Depends(require_demo_key)],
    )
    @limiter.limit("120/minute")
    async def sponsor_genie(
        request: Request, body: _SponsorGenieRequest
    ) -> JSONResponse:
        if not flags.SPONSOR_GENIE:
            raise HTTPException(status_code=404, detail="sponsor_genie_disabled")

        from app.sponsor.genie import GenieClient

        client = GenieClient()
        result = client.ask(body.conversation_id, body.query)
        return JSONResponse(content=result)

    @app.post(
        "/sponsor/narrate",
        dependencies=[Depends(require_demo_key)],
    )
    @limiter.limit("120/minute")
    async def sponsor_narrate(
        request: Request, body: _SponsorNarrateRequest
    ) -> StreamingResponse:
        if not flags.SPONSOR_VOICE:
            raise HTTPException(status_code=404, detail="sponsor_voice_disabled")

        from app.sponsor.voice_narration import VoiceUnavailable, narrate

        try:
            media_type, byte_iter = narrate(
                demo_id=body.demo_id,
                lang=body.lang,
                hospital_name=body.hospital_name,
                eta_min=body.eta_min,
            )
        except VoiceUnavailable as exc:
            # 503 (not 500) — the route itself is healthy; the upstream voice
            # path just has nothing to serve right now.
            raise HTTPException(status_code=503, detail=str(exc))

        return StreamingResponse(byte_iter, media_type=media_type)
