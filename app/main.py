import time
import concurrent.futures
from functools import lru_cache
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.settings import settings
import mlflow.deployments

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


def _fm_endpoint_count(ttl_sec: int = 60, timeout: float = 8.0) -> int | None:
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
