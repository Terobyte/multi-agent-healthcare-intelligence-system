import asyncio
import json
import logging
import os
import time
import concurrent.futures
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Optional
from uuid import uuid4
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from app.agents.booking import book_atomic
from app.schemas import BookingOutput, ReasoningPanelEvent
from app.settings import settings
import mlflow.deployments

# Forward our app loggers ("booking", "app.*") to stderr so Render's log tail
# captures saga compensation errors. basicConfig is a no-op when the root
# logger already has handlers (e.g. uvicorn --log-config); attach an explicit
# handler to our named loggers so saga compensation logs survive both modes.
_log_formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
_log_handler = logging.StreamHandler()
_log_handler.setFormatter(_log_formatter)
for _name in ("app", "booking"):
    _lgr = logging.getLogger(_name)
    _lgr.setLevel(logging.INFO)
    if not any(isinstance(h, logging.StreamHandler) for h in _lgr.handlers):
        _lgr.addHandler(_log_handler)
    _lgr.propagate = False
logger = logging.getLogger("app.main")

app = FastAPI(title="AarogyaNet")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Demo-stage protection for mutating endpoints. Public Render URL otherwise lets
# any audience member POST /book and dirty the trust calibration mid-pitch.
DEMO_KEY = os.getenv("DEMO_KEY", "")
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
# Default 500 → 429 with a usable Retry-After header.
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


def require_demo_key(x_demo_key: str = Header(default="")):
    # Empty DEMO_KEY → auth disabled (local dev). In Render env, set the secret.
    if DEMO_KEY and x_demo_key != DEMO_KEY:
        raise HTTPException(status_code=401, detail="invalid X-Demo-Key")


@lru_cache(maxsize=1)
def fm_client():
    return mlflow.deployments.get_deploy_client("databricks")


_ep_cache = {"n": None, "ts": 0.0}

# Module-level bounded executor — reused across all /health probes. Caps stuck
# threads at max_workers even when list_endpoints() hangs forever; the TTL
# cache means submit() runs at most once per ttl_sec window, so unbounded queue
# growth is also bounded in practice.
_fm_executor = concurrent.futures.ThreadPoolExecutor(
    max_workers=2, thread_name_prefix="fm-probe"
)


def reset_fm_client() -> None:
    """Invalidate the cached mlflow client and endpoint count.

    Call after Databricks token rotation to force re-authentication on the next
    /health probe without restarting the process.
    """
    fm_client.cache_clear()
    _ep_cache["n"] = None
    _ep_cache["ts"] = 0.0


def _fm_endpoint_count(ttl_sec: int = 60, timeout: float = 8.0) -> Optional[int]:
    now = time.time()
    # cache every attempt within TTL — successful or not. Render probes /health
    # every 10-30s; without stamping ts on failure too, an FM-API outage turns
    # every probe into a fresh upstream call (retry storm).
    if (now - _ep_cache["ts"]) < ttl_sec:
        return _ep_cache["n"]
    try:
        future = _fm_executor.submit(lambda: len(fm_client().list_endpoints()))
        _ep_cache["n"] = future.result(timeout=timeout)
    except Exception:
        # Throttled by ttl_sec — no log storm even during a sustained outage.
        # Keep last-known endpoint count (None on cold-start / auth failure).
        logger.warning("fm_probe_failed last_known=%s", _ep_cache["n"], exc_info=True)
    _ep_cache["ts"] = now
    return _ep_cache["n"]


@app.get("/health")
def health():
    n = _fm_endpoint_count()
    # n == 0 is a misconfig (FM API reachable but no endpoints provisioned) —
    # report degraded so a workspace with empty endpoint list doesn't show green.
    healthy = n is not None and n > 0
    return {
        "status": "ok" if healthy else "degraded",
        "fm_ok": healthy,
        "fm_endpoints": n,
        "warehouse": "configured" if settings.databricks_warehouse_id else "missing",
    }


class BookRequest(BaseModel):
    facility_id: str
    patient_id: str


@app.post("/book", response_model=BookingOutput, dependencies=[Depends(require_demo_key)])
@limiter.limit("5/minute")
def book(request: Request, req: BookRequest):
    try:
        # Validate inside the try so a malformed dict from book_atomic raises
        # ValidationError HERE, not later in FastAPI's response serializer
        # (where this except wouldn't see it).
        return BookingOutput(**book_atomic(req.facility_id, req.patient_id, {}))
    except Exception:
        logger.exception("book_endpoint_unhandled facility=%s patient=%s", req.facility_id, req.patient_id)
        return BookingOutput(
            transaction_id=None, status="REJECTED",
            resources={}, facility_id=req.facility_id,
            reason="warehouse unavailable",
        )


# Order matches the reasoning-panel pipeline. Real agents (Mubarak's wiring)
# will replace these placeholder ticks with token-by-token model output.
AGENT_ORDER = ["triage", "extractor", "validator", "router", "transfer"]


def _evt(agent: str, token: str, trace_id: str) -> str:
    payload = ReasoningPanelEvent(
        agent=agent, token=token, trace_id=trace_id,
        ts=datetime.now(timezone.utc),
    ).model_dump(mode="json")
    return f"event: {agent}\ndata: {json.dumps(payload)}\n\n"


@app.get("/sse")
async def sse(session_id: str):
    """Server-Sent Events stream of agent reasoning tokens.

    Event vocabulary (contract for ReasoningPanel.tsx):
      triage | extractor | validator | router | transfer | stream_tick | ping | done | error
    Terminal: `event: done` with the final session payload.
    Heartbeat: an initial `event: ping` is always emitted; an inter-tick ping
    fires only when an agent step takes >15s (placeholder cadence completes in
    ~1s and never triggers). Once real agent calls are wired in, swap to a
    parallel asyncio.create_task that pings on a wall-clock interval.
    """
    trace_id = str(uuid4())

    async def gen():
        # Initial ping confirms liveness to the client before the first agent
        # tick — and gives the proxy a byte to flush so it doesn't buffer the
        # response. Without it, an exception before the first yield closes the
        # connection silently with no body.
        yield "event: ping\ndata: {}\n\n"
        last_ping = time.time()
        try:
            for agent in AGENT_ORDER:
                yield _evt(agent, f"{agent} starting", trace_id)
                await asyncio.sleep(0.2)  # placeholder cadence; real agents stream tokens
                yield _evt(agent, f"{agent} done", trace_id)
                # Render/Cloudflare idle-close streaming connections after
                # ~30-60s. Emit a ping if more than 15s elapsed since the last
                # frame so long-running real agents don't drop the stream.
                if time.time() - last_ping > 15:
                    yield "event: ping\ndata: {}\n\n"
                    last_ping = time.time()
            yield f"event: done\ndata: {json.dumps({'session_id': session_id, 'trace_id': trace_id})}\n\n"
        except Exception as e:
            logger.exception("sse_failed trace=%s", trace_id)
            yield f"event: error\ndata: {json.dumps({'code':'sse_error','message':str(e)[:200]})}\n\n"

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"},
    )


# Demo insurance: if Llama 3.3 70B endpoint 429s on stage, frontend swaps to
# /sse_demo and replays a recorded transcript at human-readable cadence.
_DEMO_TRANSCRIPT = Path(__file__).parent / "agents" / "_demo_transcript.sse"


@app.get("/sse_demo")
async def sse_demo(session_id: str):
    if not _DEMO_TRANSCRIPT.exists():
        raise HTTPException(status_code=503, detail="transcript not recorded")
    text = _DEMO_TRANSCRIPT.read_text()

    async def gen():
        saw_done = False
        for chunk in text.split("\n\n"):
            chunk = chunk.strip()
            if not chunk:
                continue
            if "event: done" in chunk:
                saw_done = True
            yield chunk + "\n\n"
            await asyncio.sleep(0.25)
        # Frontend EventSource hangs forever waiting for `done`. If the canned
        # transcript is malformed (no done frame), surface a synthetic one so
        # the panel cleanly closes instead of looking frozen.
        if not saw_done:
            logger.warning("sse_demo_transcript_missing_done session=%s", session_id)
            yield 'event: error\ndata: {"code":"demo_transcript_invalid","message":"no done frame"}\n\n'
            yield f'event: done\ndata: {{"session_id":"{session_id}"}}\n\n'

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"},
    )
