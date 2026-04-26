import time
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


def _fm_endpoint_count(ttl_sec: int = 60) -> int | None:
    now = time.time()
    # cache every attempt within TTL — successful or not. Render probes /health
    # every 10-30s; without stamping ts on failure too, an FM-API outage turns
    # every probe into a fresh upstream call (retry storm).
    if (now - _ep_cache["ts"]) < ttl_sec:
        return _ep_cache["n"]
    try:
        _ep_cache["n"] = len(fm_client().list_endpoints())
    except Exception:
        pass  # keep last-known (None on cold-start failure)
    _ep_cache["ts"] = now
    return _ep_cache["n"]


@app.get("/health")
def health():
    n = _fm_endpoint_count()
    return {
        "status": "ok" if n is not None else "degraded",
        "fm_endpoints": n,
        "warehouse": settings.databricks_warehouse_id[:8] + "...",
    }
