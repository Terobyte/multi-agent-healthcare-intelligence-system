import asyncio
import json
import logging
import time
import concurrent.futures
from datetime import datetime, timezone
from functools import lru_cache
from typing import Optional
from uuid import uuid4
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from app.agents.booking import book_atomic
from app.schemas import BookingOutput, ReasoningPanelEvent
from app.settings import settings
import mlflow.deployments

# Forward our app loggers ("booking", "app.*") to stderr so Render's log tail
# captures saga compensation errors. uvicorn's default config only configures
# its own loggers; named loggers are silent without this.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("app.main")

app = FastAPI(title="AarogyaNet")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


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
        pass  # keep last-known (None on cold-start / timeout / auth failure)
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


@app.post("/book", response_model=BookingOutput)
def book(req: BookRequest):
    try:
        return book_atomic(req.facility_id, req.patient_id, {})
    except Exception:
        # Warehouse cold-start / auth / network failure escapes the saga's
        # internal try blocks (which only wrap individual queries). Return a
        # structured REJECTED so the UI gets a usable BookingOutput shape
        # instead of FastAPI's bare {"detail":"Internal Server Error"}.
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
    Heartbeat: `event: ping` every 15s so reverse proxies don't idle-close.
    """
    trace_id = str(uuid4())

    async def gen():
        try:
            for agent in AGENT_ORDER:
                yield _evt(agent, f"{agent} starting", trace_id)
                await asyncio.sleep(0.2)  # placeholder cadence; real agents stream tokens
                yield _evt(agent, f"{agent} done", trace_id)
            yield f"event: done\ndata: {json.dumps({'session_id': session_id, 'trace_id': trace_id})}\n\n"
        except Exception as e:
            logger.exception("sse_failed trace=%s", trace_id)
            yield f"event: error\ndata: {json.dumps({'code':'sse_error','message':str(e)[:200]})}\n\n"

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"},
    )
