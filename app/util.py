"""PII handling helpers per DPDP Act 2023.

Apply at every system boundary that touches Delta or LLM context:
  - hash_patient_id: opaque pseudonym for patient identifiers
  - round_geo: 2-decimal-degree grid (~1km) for lat/lng

Never log or persist the raw patient_id or coordinates after this layer.
"""
import hashlib
import os

_DEV_SALT = "aarogyanet-dev-salt-do-not-use-in-prod"


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


def hash_patient_id(patient_id: str) -> str:
    """Salted SHA-256 → 16-hex-char prefix prefixed with `p_`.

    16 hex chars = 64 bits = ~10^19 keyspace; collision probability for a
    realistic patient population (10^7) is negligible.
    """
    return "p_" + hashlib.sha256((_resolve_salt() + patient_id).encode()).hexdigest()[:16]


def round_geo(lat: float, lon: float) -> tuple[float, float]:
    """Coarsen coordinates to a ~1km grid (2 decimal degrees ≈ 1.1km at equator)."""
    return round(lat, 2), round(lon, 2)
