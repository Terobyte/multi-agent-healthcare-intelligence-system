import asyncio
import json
import logging
import os
import re
import time
import concurrent.futures
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Optional
from uuid import uuid4
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel, Field
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.middleware.base import BaseHTTPMiddleware
from app.agents.booking import book_atomic
from app.agents.router import recommend as _recommend
from app.agents.triage import triage as _triage_agent
from app.schemas import BookingOutput, ReasoningPanelEvent, TriageOutput
from app.settings import settings
from contracts.schemas import RankedHospital
import mlflow.deployments

# bug #20: scrub Bearer/dapi token shapes from log records and formatted output.
_TOKEN_PATTERNS = [
    re.compile(r"Bearer\s+dapi[a-zA-Z0-9._-]+", re.IGNORECASE),
    re.compile(r"\bdapi[a-zA-Z0-9._-]{8,}", re.IGNORECASE),
    re.compile(r"Authorization:\s*\S+", re.IGNORECASE),
]


def _scrub(text: str) -> str:
    for pat in _TOKEN_PATTERNS:
        text = pat.sub("[REDACTED]", text)
    return text


class _ScrubbingFormatter(logging.Formatter):
    """Second-pass scrub on the fully-rendered string, including the formatted
    traceback (source lines come from disk — no filter can reach them)."""

    def format(self, record: logging.LogRecord) -> str:
        return _scrub(super().format(record))

    def formatException(self, ei) -> str:
        return _scrub(super().formatException(ei))


# bug #20: install a global LogRecord factory that scrubs at creation time.
# Filters run only on the originating logger; a global factory ensures EVERY
# handler (caplog, test ListHandler, third-party log shippers) sees clean data.
# Idempotent across module reloads via the `_aarogyanet_scrub` marker attribute.
_existing_factory = logging.getLogRecordFactory()
if not getattr(_existing_factory, "_aarogyanet_scrub", False):
    _orig_record_factory = _existing_factory

    def _scrubbing_record_factory(*args, **kwargs):
        record = _orig_record_factory(*args, **kwargs)
        try:
            record.msg = _scrub(record.getMessage())
            record.args = ()
        except Exception:
            pass
        if record.exc_info:
            etype, evalue, _tb = record.exc_info
            if evalue is not None:
                original_args = "".join(repr(a) for a in evalue.args)
                # If the exception text carried a token, drop the traceback —
                # Python's traceback formatter reads source from disk and would
                # re-leak the raise statement's literal arguments.
                if original_args != _scrub(original_args):
                    try:
                        clean = (etype or RuntimeError)(*[_scrub(str(a)) for a in evalue.args])
                    except Exception:
                        clean = RuntimeError(_scrub(str(evalue)))
                    record.exc_info = (type(clean), clean, None)
                else:
                    try:
                        evalue.args = tuple(_scrub(str(a)) for a in evalue.args)
                    except Exception:
                        pass
        return record

    _scrubbing_record_factory._aarogyanet_scrub = True  # type: ignore[attr-defined]
    logging.setLogRecordFactory(_scrubbing_record_factory)

_log_formatter = _ScrubbingFormatter("%(asctime)s %(levelname)s %(name)s %(message)s")
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

# CORS: env-driven allowlist (comma-separated). Default "*" preserves the demo
# UX, but production sets CORS_ORIGINS to a specific origin so the public Render
# URL can't be hit by arbitrary third parties carrying X-Demo-Key in a browser.
_CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_CORS_ORIGINS or ["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# Hard cap request body size at 64 KB. Triage prompts + booking JSON fit easily
# inside this; anything larger is either misconfig or a memory-exhaustion probe.
# We reject pre-read via Content-Length so a 10 GB upload never hits the worker.
MAX_REQUEST_BYTES = 64 * 1024


class _BodySizeLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        cl = request.headers.get("content-length")
        if cl is not None:
            try:
                if int(cl) > MAX_REQUEST_BYTES:
                    return JSONResponse(
                        status_code=413,
                        content={"detail": f"request body exceeds {MAX_REQUEST_BYTES} bytes"},
                    )
            except ValueError:
                # Malformed Content-Length — treat as suspicious, refuse.
                return JSONResponse(status_code=400, content={"detail": "invalid Content-Length"})
        return await call_next(request)


app.add_middleware(_BodySizeLimitMiddleware)

# Demo-stage protection for mutating endpoints. Public Render URL otherwise lets
# any audience member POST /book and dirty the trust calibration mid-pitch.
DEMO_KEY = os.getenv("DEMO_KEY", "")
DEV_MODE = os.getenv("AAROGYANET_DEV") == "1"


def _client_key(request: Request) -> str:
    """Rate-limit key that survives Render's reverse proxy.

    `get_remote_address` returns the proxy IP when X-Forwarded-For is present —
    that collapses every Render user onto a single bucket and makes the limit
    trivially DoS-able. Read the first XFF entry instead, fall back to the
    direct peer address only if XFF is absent or empty.
    """
    xff = request.headers.get("x-forwarded-for", "")
    if xff:
        first = xff.split(",")[0].strip()
        if first:
            return first
    return get_remote_address(request)


limiter = Limiter(key_func=_client_key)
app.state.limiter = limiter
# Default 500 → 429 with a usable Retry-After header.
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


def require_demo_key(x_demo_key: str = Header(default="")):
    # bug #1: fail-closed by default. Without DEMO_KEY env, the only way to get
    # unauthenticated access is to explicitly set AAROGYANET_DEV=1. Prevents an
    # env-var typo on Render from silently opening /book to the world.
    if not DEMO_KEY:
        if DEV_MODE:
            return  # explicit dev opt-in
        raise HTTPException(
            status_code=401,
            detail="DEMO_KEY not configured (set DEMO_KEY env, or AAROGYANET_DEV=1 for local)",
        )
    if x_demo_key != DEMO_KEY:
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
    if (now - _ep_cache["ts"]) < ttl_sec:
        return _ep_cache["n"]
    try:
        future = _fm_executor.submit(lambda: len(fm_client().list_endpoints()))
        _ep_cache["n"] = future.result(timeout=timeout)
        _ep_cache["ts"] = now
    except Exception:
        # Don't refresh ts on failure — otherwise a transient outage pins the
        # cache to "degraded" for ttl_sec even after the endpoint recovers.
        # Throttled to ttl_sec/2 below to avoid a log storm during sustained outage.
        if (now - _ep_cache.get("ts_log", 0.0)) > (ttl_sec / 2):
            logger.warning("fm_probe_failed last_known=%s", _ep_cache["n"], exc_info=True)
            _ep_cache["ts_log"] = now
    return _ep_cache["n"]


@app.get("/health")
async def health():
    n = await asyncio.to_thread(_fm_endpoint_count)
    healthy = n is not None and n > 0
    return {
        "status": "ok" if healthy else "degraded",
        "fm_ok": healthy,
        "fm_endpoints": n,
        "warehouse": "configured" if settings.databricks_warehouse_id else "missing",
    }


class BookRequest(BaseModel):
    facility_id: str = Field(max_length=64)
    patient_id: str = Field(max_length=64)


@app.post("/book", response_model=BookingOutput, dependencies=[Depends(require_demo_key)])
@limiter.limit("5/minute")
def book(request: Request, req: BookRequest):
    return BookingOutput(**book_atomic(req.facility_id, req.patient_id, {}))


@app.exception_handler(Exception)
async def _scrubbed_500(request: Request, exc: Exception):
    # Infra failures (DB outage, mlflow client throwing, etc.) MUST surface as
    # 5xx so monitoring sees them — the prior try/except returning 200/REJECTED
    # masked outages. The LogRecord factory above scrubs Bearer/dapi tokens out
    # of logs; this handler scrubs them out of the JSON response body too.
    logger.exception("unhandled_exception path=%s", request.url.path)
    return JSONResponse(status_code=500, content={"detail": "internal error"})


# Order matches the reasoning-panel pipeline. Real agents (Mubarak's wiring)
# will replace these placeholder ticks with token-by-token model output.
AGENT_ORDER = ["triage", "extractor", "validator", "router", "transfer"]

# Wall-clock cadence for SSE keepalive. nginx/Render LB idle-close at ~30-60s of
# silence — pinging every 10s keeps the connection alive even when agents stall.
SSE_HEARTBEAT_INTERVAL_S = float(os.getenv("SSE_HEARTBEAT_INTERVAL_S", "10"))


def _evt(agent: str, token: str, trace_id: str) -> str:
    payload = ReasoningPanelEvent(
        agent=agent, token=token, trace_id=trace_id,
        ts=datetime.now(timezone.utc),
    ).model_dump(mode="json")
    return f"event: {agent}\ndata: {json.dumps(payload)}\n\n"


@app.get("/sse")
async def sse(session_id: str, request: Request):
    """SSE stream of agent reasoning. Event vocab: triage|extractor|validator|
    router|transfer|stream_tick|ping|done|error. Bug #13: aborts on disconnect.
    """
    trace_id = str(uuid4())

    async def gen():
        # Heartbeat MUST run on a wall-clock timer, not piggy-back on agent
        # emission. Old impl only pinged when an agent finished AND >15s had
        # passed — so fast agents (no gate trip) and slow agents (blocked in
        # await) both broke it, and the proxy idle-closed the stream.
        queue: asyncio.Queue = asyncio.Queue()
        DONE = object()

        async def heartbeat():
            try:
                while True:
                    await asyncio.sleep(SSE_HEARTBEAT_INTERVAL_S)
                    await queue.put("event: ping\ndata: {}\n\n")
            except asyncio.CancelledError:
                pass

        async def producer():
            try:
                for agent in AGENT_ORDER:
                    if await request.is_disconnected():
                        logger.info("sse_client_disconnected trace=%s at=%s", trace_id, agent)
                        return
                    await queue.put(_evt(agent, f"{agent} starting", trace_id))
                    await asyncio.sleep(0.2)
                    await queue.put(_evt(agent, f"{agent} done", trace_id))
                await queue.put(
                    f"event: done\ndata: {json.dumps({'session_id': session_id, 'trace_id': trace_id})}\n\n"
                )
            except Exception as e:
                logger.exception("sse_failed trace=%s", trace_id)
                await queue.put(
                    f"event: error\ndata: {json.dumps({'code':'sse_error','message':str(e)[:200]})}\n\n"
                )
                await queue.put(
                    f"event: done\ndata: {json.dumps({'session_id': session_id, 'trace_id': trace_id})}\n\n"
                )
            finally:
                await queue.put(DONE)

        hb_task = asyncio.create_task(heartbeat())
        prod_task = asyncio.create_task(producer())

        yield "event: ping\ndata: {}\n\n"
        try:
            while True:
                chunk = await queue.get()
                if chunk is DONE:
                    break
                yield chunk
        finally:
            hb_task.cancel()
            if not prod_task.done():
                prod_task.cancel()
            for t in (hb_task, prod_task):
                try:
                    await t
                except (asyncio.CancelledError, Exception):
                    pass

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
    """Bug #14: always responds as text/event-stream — missing transcript
    becomes an SSE error frame, not an HTTPException 503."""
    async def gen():
        if not _DEMO_TRANSCRIPT.exists():
            logger.warning("sse_demo_transcript_missing path=%s", _DEMO_TRANSCRIPT)
            yield 'event: error\ndata: {"code":"transcript_not_recorded","message":"demo transcript missing"}\n\n'
            yield f'event: done\ndata: {{"session_id":"{session_id}"}}\n\n'
            return
        # Off-load disk I/O so a slow filesystem (Render's container layer can
        # stall on cold reads) doesn't block the FastAPI event loop while the
        # transcript is loaded.
        text = await asyncio.to_thread(_DEMO_TRANSCRIPT.read_text)
        saw_done = False
        for chunk in text.split("\n\n"):
            chunk = chunk.strip()
            if not chunk:
                continue
            if "event: done" in chunk:
                saw_done = True
            yield chunk + "\n\n"
            await asyncio.sleep(0.25)
        if not saw_done:
            logger.warning("sse_demo_transcript_missing_done session=%s", session_id)
            yield 'event: error\ndata: {"code":"demo_transcript_invalid","message":"no done frame"}\n\n'
            yield f'event: done\ndata: {{"session_id":"{session_id}"}}\n\n'

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"},
    )


class TriageRequest(BaseModel):
    user_text: str = Field(max_length=4000)
    language: str = Field(default="en", max_length=8)


@app.post("/triage", response_model=TriageOutput)
@limiter.limit("20/minute")
async def triage_endpoint(request: Request, req: TriageRequest):
    """Symptom text → TriageOutput via Llama 3.3 70B (keyword fallback on error).

    Wraps the synchronous triage() call in asyncio.to_thread so the FastAPI
    event loop stays unblocked during the Databricks LLM round-trip (~2-8 s).
    """
    return await asyncio.to_thread(_triage_agent, req.user_text, req.language)


class RecommendRequest(BaseModel):
    user_text: str = Field(max_length=4000)
    city: str = Field(default="mumbai", max_length=80)
    language: str = Field(default="en", max_length=8)


class RecommendResponse(BaseModel):
    triage: TriageOutput
    hospitals: list[RankedHospital]
    fast_path: bool


@app.post("/recommend", response_model=RecommendResponse)
@limiter.limit("20/minute")
async def recommend_endpoint(request: Request, req: RecommendRequest):
    """Symptom text → triage result + ranked hospitals (combined pipeline).

    Runs triage (Llama 3.3 70B with keyword fallback) then the router agent
    (trust × bed-availability × specialty × distance) in sequence.  Both calls
    are wrapped in asyncio.to_thread so DB + LLM round-trips never block the
    FastAPI event loop.

    Returns a TriageOutput, a ranked list of hospitals, and the fast_path flag
    so callers get the full routing decision in a single HTTP round-trip.
    """
    triage_result = await asyncio.to_thread(_triage_agent, req.user_text, req.language)
    hospitals = await asyncio.to_thread(_recommend, triage_result, req.city)
    return RecommendResponse(
        triage=triage_result,
        hospitals=hospitals,
        fast_path=triage_result.fast_path,
    )
