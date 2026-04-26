"""PII handling helpers per DPDP Act 2023.

Apply at every system boundary that touches Delta or LLM context:
  - hash_patient_id: opaque pseudonym for patient identifiers
  - round_geo: 2-decimal-degree grid (~1km) for lat/lng

Never log or persist the raw patient_id or coordinates after this layer.
"""
import hashlib
import os
import threading

_DEV_SALT = "aarogyanet-dev-salt-do-not-use-in-prod"

# Cache the resolved salt across calls so we don't hit os.getenv on every
# hash_patient_id() invocation (the hot path for /book and /transcript).
# Lazy: populated on first use, NOT at module import — that lets tests still
# `monkeypatch.setenv(...)` then `importlib.reload(util)` to exercise the
# fail-loud branch without crashing module load when the env is unset.
# `reset_salt_cache()` is the public knob for env rotation in long-running
# processes (token refresh handlers, ops dashboards).
_SALT_CACHE: str | None = None
_SALT_CACHE_LOCK = threading.Lock()


def _resolve_salt() -> str:
    """Pick the salt at call time, not import time.

    Fail-loud rule (bug #4): if PII_SALT is not set AND AAROGYANET_DEV is not
    set, refuse to hash. This prevents the dev salt from silently shipping to
    production where its predictability turns hashes into reversible mappings.
    """
    salt = os.getenv("PII_SALT")
    if salt:
        return salt
    if os.getenv("AAROGYANET_DEV") == "1":
        return _DEV_SALT
    raise RuntimeError(
        "PII_SALT is not set. Refusing to hash with the dev fallback salt. "
        "Set PII_SALT in your environment, or AAROGYANET_DEV=1 to opt into the "
        "insecure dev salt explicitly."
    )


def reset_salt_cache() -> None:
    """Drop the cached salt so the next hash_patient_id() re-reads the env.

    Use after rotating PII_SALT in a long-running process. Without this, the
    process would keep hashing with the previous salt until restart.
    """
    global _SALT_CACHE
    with _SALT_CACHE_LOCK:
        _SALT_CACHE = None


def _get_salt() -> str:
    """Return the cached salt, populating it from _resolve_salt() on first call.

    Double-checked locking keeps the steady-state hot path lock-free once the
    cache is warm: the outer read sees a non-None _SALT_CACHE and returns
    immediately. Two concurrent first-callers will both fall through to the
    locked block, but the inner check guarantees only one runs _resolve_salt().
    """
    cached = _SALT_CACHE
    if cached is not None:
        return cached
    with _SALT_CACHE_LOCK:
        # Re-check under the lock — another thread may have populated it.
        if _SALT_CACHE is not None:
            return _SALT_CACHE
        salt = _resolve_salt()
        globals()["_SALT_CACHE"] = salt
        return salt


def hash_patient_id(patient_id: str) -> str:
    """Salted SHA-256 → 16-hex-char prefix prefixed with `p_`.

    16 hex chars = 64 bits = ~10^19 keyspace; collision probability for a
    realistic patient population (10^7) is negligible.
    """
    return "p_" + hashlib.sha256((_get_salt() + patient_id).encode()).hexdigest()[:16]


def round_geo(lat: float, lon: float) -> tuple[float, float]:
    """Coarsen coordinates to a ~1km grid (2 decimal degrees ≈ 1.1km at equator)."""
    return round(lat, 2), round(lon, 2)
