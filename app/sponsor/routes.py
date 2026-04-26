"""FastAPI route registrar for the sponsor stack.

Single entry point :func:`register` that ``app.main`` calls once after the
``FastAPI`` app and ``slowapi.Limiter`` are constructed. Each route is mounted
only when its env flag is true, and every public route is gated by
``Depends(require_demo_key)`` (bug #1 doctrine).
"""
from __future__ import annotations

import asyncio
import logging
import re
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, ConfigDict, Field
from slowapi import Limiter

from app.sponsor.flags import flags


logger = logging.getLogger(__name__)


# Strip ASCII control characters from free-text payloads before they reach
# the agent — defense-in-depth against log/control-character injection. The
# agent also has its own scrub pipeline; this is just a route-level pre-filter.
_CONTROL_CHARS = re.compile(r"[\x00-\x1f\x7f]")


def sanitize(text: str) -> str:
    """Strip control characters from sponsor route free-text input."""
    if not text:
        return text
    return _CONTROL_CHARS.sub("", text)


class _SponsorTriageRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    symptoms: str = Field(max_length=2000)
    language: str = Field(default="en", max_length=8)


class _SponsorGenieRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    query: str = Field(max_length=500)
    conversation_id: str | None = Field(
        default=None, max_length=128, pattern=r"^[A-Za-z0-9_-]+$"
    )


class _SponsorNarrateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    demo_id: str = Field(max_length=8, pattern=r"^[A-Za-z0-9_-]+$")
    lang: str = Field(default="hi", max_length=4)
    hospital_name: str = Field(default="", max_length=120)
    # eta_min must be at least 1 — telling a patient "ambulance arrives in
    # 0 minutes" is a UX bug and a data-quality smell.
    eta_min: int = Field(default=1, ge=1, le=120)


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
            logger.warning(
                "sponsor probe attempt while agent_bricks disabled (client=%s)",
                request.client.host if request.client else "?",
            )
            raise HTTPException(status_code=404, detail="sponsor_agent_bricks_disabled")

        from app.sponsor.agent_bricks import run_triage

        cleaned_symptoms = sanitize(body.symptoms)
        # bug #115: run_triage calls Databricks model serving synchronously.
        # Without to_thread the FastAPI event loop stalls for the full LLM
        # round-trip and every other concurrent request queues behind it.
        result = await asyncio.to_thread(run_triage, cleaned_symptoms, body.language)
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
            logger.warning(
                "sponsor probe attempt while genie disabled (client=%s)",
                request.client.host if request.client else "?",
            )
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
            logger.warning(
                "sponsor probe attempt while voice disabled (client=%s)",
                request.client.host if request.client else "?",
            )
            raise HTTPException(status_code=404, detail="sponsor_voice_disabled")

        from app.sponsor.voice_narration import (
            MAX_NARRATE_BYTES,
            VoiceUnavailable,
            narrate,
        )

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

        # Route-level cap as a second defense in case voice_narration's own
        # cap is bypassed (e.g. a future code path that yields from a file).
        def _capped() -> Any:
            streamed = 0
            for chunk in byte_iter:
                streamed += len(chunk)
                if streamed >= MAX_NARRATE_BYTES:
                    logger.warning(
                        "sponsor narrate response exceeded %d bytes (too_large); aborting",
                        MAX_NARRATE_BYTES,
                    )
                    return
                yield chunk

        return StreamingResponse(_capped(), media_type=media_type)
