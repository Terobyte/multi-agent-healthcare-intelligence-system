"""PII handling helpers per DPDP Act 2023.

Apply at every system boundary that touches Delta or LLM context:
  - hash_patient_id: opaque pseudonym for patient identifiers
  - round_geo: 2-decimal-degree grid (~1km) for lat/lng

Never log or persist the raw patient_id or coordinates after this layer.
"""
import hashlib
import os

# PII_SALT must be set in production via Render Secret env. The dev fallback
# guarantees the module imports in tests / local smokes but produces hashes
# that are NOT safe for any data leaving a developer machine.
_SALT = os.getenv("PII_SALT", "aarogyanet-dev-salt-do-not-use-in-prod")


def hash_patient_id(patient_id: str) -> str:
    """Salted SHA-256 → 16-hex-char prefix prefixed with `p_`.

    16 hex chars = 64 bits = ~10^19 keyspace; collision probability for a
    realistic patient population (10^7) is negligible.
    """
    return "p_" + hashlib.sha256((_SALT + patient_id).encode()).hexdigest()[:16]


def round_geo(lat: float, lon: float) -> tuple[float, float]:
    """Coarsen coordinates to a ~1km grid (2 decimal degrees ≈ 1.1km at equator)."""
    return round(lat, 2), round(lon, 2)
