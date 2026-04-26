"""ValidatorAgent — two-model trust verification wrapper for live API responses.

Reads pre-computed scores from workspace.default.gold_trust_two_model, which
stores per-facility per-factor predictions from two independent LLMs:
  v1  — Llama 3.3 70B (Extractor role)
  v2  — Llama 4 Maverick (Validator role)

Agreement rule: max factor delta ≤ 0.20 across (bed, oxygen, drug, specialist)
→ 'two-model-verified'.  Disagreement → 'models-disagree' (conservative: MIN).

The table is pre-built by scripts/databricks/10_two_model_verify.sql; this agent
is a read-only query wrapper — no LLM call happens at query time, so latency is
bounded by the SQL warehouse cold-start, not model inference.

On any DB error (timeout, auth, warehouse unavailable) the agent returns a
deterministic fallback TrustScorerOutput with agreement=False and confidence=0.0
so the SSE stream always terminates cleanly rather than propagating a 500.

v_trust_calibrated: when available (Mubarak's calibration view), the agent reads
trust_calibrated for the facility and surfaces it in TrustScorerOutput so the
caller can show outcome-adjusted trust without a separate query.
"""
import logging
from typing import Optional

from app.db import warehouse_query
from app.schemas import FactorWithReasoning, TrustScorerOutput

logger = logging.getLogger("validator")

# ---------------------------------------------------------------------------
# Agreement threshold — must match 10_two_model_verify.sql
# ---------------------------------------------------------------------------
_AGREEMENT_THRESHOLD = 0.20

# ---------------------------------------------------------------------------
# SQL
# ---------------------------------------------------------------------------

# Primary query: join gold_trust_two_model + v_trust_calibrated so a single
# round-trip fetches both raw blended trust and the outcome-adjusted score.
_QUERY_CAL = """
SELECT
  t.facility_id,
  t.v1_p_bed,       t.v2_p_bed,
  t.v1_p_oxygen,    t.v2_p_oxygen,
  t.v1_p_drug,      t.v2_p_drug,
  t.v1_p_specialist,t.v2_p_specialist,
  t.v1_ci,          t.v2_ci,
  t.v1_reasoning,   t.v2_reasoning,
  t.max_factor_disagreement,
  t.verification_status,
  t.p_bed_blended, t.p_oxygen_blended, t.p_drug_blended, t.p_specialist_blended,
  COALESCE(tc.trust_calibrated, NULL) AS trust_calibrated
FROM workspace.default.gold_trust_two_model t
LEFT JOIN workspace.default.v_trust_calibrated tc
  ON t.facility_id = tc.facility_id
WHERE t.facility_id = ?
LIMIT 1
"""

# Fallback: v_trust_calibrated may not exist in all deployments.
_QUERY_SIMPLE = """
SELECT
  t.facility_id,
  t.v1_p_bed,       t.v2_p_bed,
  t.v1_p_oxygen,    t.v2_p_oxygen,
  t.v1_p_drug,      t.v2_p_drug,
  t.v1_p_specialist,t.v2_p_specialist,
  t.v1_ci,          t.v2_ci,
  t.v1_reasoning,   t.v2_reasoning,
  t.max_factor_disagreement,
  t.verification_status,
  t.p_bed_blended, t.p_oxygen_blended, t.p_drug_blended, t.p_specialist_blended
FROM workspace.default.gold_trust_two_model t
WHERE t.facility_id = ?
LIMIT 1
"""

_COLS_CAL = (
    "facility_id",
    "v1_p_bed", "v2_p_bed",
    "v1_p_oxygen", "v2_p_oxygen",
    "v1_p_drug", "v2_p_drug",
    "v1_p_specialist", "v2_p_specialist",
    "v1_ci", "v2_ci",
    "v1_reasoning", "v2_reasoning",
    "max_factor_disagreement",
    "verification_status",
    "p_bed_blended", "p_oxygen_blended", "p_drug_blended", "p_specialist_blended",
    "trust_calibrated",
)

_COLS_SIMPLE = _COLS_CAL[:-1]  # drop trust_calibrated


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe_float(val, default: float = 0.0) -> float:
    """Coerce a DB value to float; returns default on None / invalid."""
    try:
        return float(val) if val is not None else default
    except (TypeError, ValueError):
        return default


def _clamp(val: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, val))


def _blended_trust(row: dict) -> float:
    """Compute blended trust as the mean of the 4 blended factor scores."""
    factors = [
        _safe_float(row.get("p_bed_blended")),
        _safe_float(row.get("p_oxygen_blended")),
        _safe_float(row.get("p_drug_blended")),
        _safe_float(row.get("p_specialist_blended")),
    ]
    return _clamp(round(sum(factors) / 4.0, 3))


def _build_factor(
    name: str,
    v1: Optional[float],
    v2: Optional[float],
    verification_status: str,
    extractor_model: str = "databricks-meta-llama-3-3-70b-instruct",
    validator_model: str = "databricks-llama-4-maverick",
) -> FactorWithReasoning:
    """Construct a FactorWithReasoning for a single trust factor.

    Uses the same conservative blending rule as 10_two_model_verify.sql:
      - both models present + max_delta ≤ 0.20 → average
      - both present + disagreement → MIN (conservative)
      - single model → use whichever is available
    """
    if v1 is not None and v2 is not None:
        delta = abs(v1 - v2)
        if delta <= _AGREEMENT_THRESHOLD:
            value = _clamp(round((v1 + v2) / 2.0, 3))
            source = f"{extractor_model}+{validator_model} (averaged, delta={delta:.2f})"
        else:
            value = _clamp(round(min(v1, v2), 3))
            source = f"{extractor_model}+{validator_model} (conservative min, delta={delta:.2f})"
    elif v1 is not None:
        value = _clamp(round(v1, 3))
        source = extractor_model
    elif v2 is not None:
        value = _clamp(round(v2, 3))
        source = validator_model
    else:
        value = 0.0
        source = "no data"

    reasoning = (
        f"v1={v1:.2f} v2={v2:.2f} status={verification_status}"
        if v1 is not None and v2 is not None
        else f"single model only; v1={v1} v2={v2}"
    )

    return FactorWithReasoning(
        value=value,
        reasoning=reasoning[:2000],
        source=source[:200],
    )


def _fallback(facility_id: str) -> TrustScorerOutput:
    """Return a minimal TrustScorerOutput when the DB is unavailable.

    agreement=False and all factor values at 0.0 signal to the caller that
    data is absent, not that the hospital is untrustworthy.
    """
    _no_data = FactorWithReasoning(
        value=0.0,
        reasoning="validator DB unavailable",
        source="fallback",
    )
    return TrustScorerOutput(
        facility_id=facility_id,
        factors={
            "bed": _no_data,
            "oxygen": _no_data,
            "drug": _no_data,
            "specialist": _no_data,
        },
        trust=0.0,
        trust_calibrated=0.0,
        extractor_reasoning="unavailable",
        validator_reasoning="unavailable",
        agreement=False,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def validate(
    facility,  # str facility_id  OR  dict with at least 'facility_id'
    request: Optional[dict] = None,  # optional patient/request context (ignored for DB query)
) -> TrustScorerOutput:
    """Return two-model trust verification for a facility.

    Accepts two calling styles for backward compatibility:

      1. ``validate(facility_id: str)`` — legacy; used by main.py.
      2. ``validate(facility: dict, request: dict)`` — enriched pipeline form.
         ``facility`` must contain ``facility_id``.  If it also carries
         ``trust_calibrated`` that value is used as the calibrated score when
         the DB lookup returns NULL (e.g. v_trust_calibrated not yet populated).
         ``request`` (specialty / urgency / required_bed_type) is accepted for
         future per-request filtering but not used in the DB query today.

    Queries gold_trust_two_model (pre-built by 10_two_model_verify.sql) and
    surfaces per-factor Extractor vs. Validator scores, blended trust, and
    outcome-calibrated trust when v_trust_calibrated is available.

    Falls back to a zero-trust placeholder on any DB error so callers never
    see a 500 from this path.

    Args:
        facility: Gold table facility identifier string (e.g. "1234") OR a
            facility dict containing at least ``facility_id``.
        request: Optional patient/request context dict (e.g. specialty,
            urgency, required_bed_type). Currently unused in the DB query.

    Returns:
        TrustScorerOutput with agreement flag, factor breakdown, and reasonings.
    """
    # --- normalise caller styles -----------------------------------------
    if isinstance(facility, dict):
        facility_id: str = str(facility.get("facility_id", ""))
        # Pre-computed calibrated trust from the router/upstream pipeline.
        # Used as the fallback when the DB row lacks trust_calibrated.
        _caller_trust_cal: Optional[float] = (
            float(facility["trust_calibrated"])
            if facility.get("trust_calibrated") is not None
            else None
        )
    else:
        facility_id = str(facility)
        _caller_trust_cal = None
    # ---------------------------------------------------------------------

    # bug #34: reject blank/empty facility_id BEFORE hitting warehouse_query.
    # An empty string would still parameterize the SQL `WHERE facility_id = ?`,
    # returning either a wrong row (if facility_id="" exists) or scanning the
    # entire calibrated table — neither is meaningful, both cost a round-trip.
    if not facility_id or not facility_id.strip():
        raise ValueError("facility_id must be a non-empty string")

    row: Optional[dict] = None
    use_cal = True

    try:
        rows = warehouse_query(_QUERY_CAL, [facility_id])
        if rows:
            row = dict(zip(_COLS_CAL, rows[0]))
    except Exception:
        logger.warning("validator_cal_query_failed facility=%s — retrying without calibration", facility_id)
        use_cal = False
        try:
            rows = warehouse_query(_QUERY_SIMPLE, [facility_id])
            if rows:
                row = dict(zip(_COLS_SIMPLE, rows[0]))
        except Exception:
            logger.exception("validator_query_failed facility=%s — returning fallback", facility_id)
            return _fallback(facility_id)

    if row is None:
        logger.warning("validator_no_two_model_row facility=%s — facility not in gold_trust_two_model", facility_id)
        return _fallback(facility_id)

    verification_status: str = str(row.get("verification_status") or "single-model")
    agreement = verification_status == "two-model-verified"

    factors = {
        "bed": _build_factor(
            "bed",
            v1=_safe_float(row.get("v1_p_bed")) if row.get("v1_p_bed") is not None else None,
            v2=_safe_float(row.get("v2_p_bed")) if row.get("v2_p_bed") is not None else None,
            verification_status=verification_status,
        ),
        "oxygen": _build_factor(
            "oxygen",
            v1=_safe_float(row.get("v1_p_oxygen")) if row.get("v1_p_oxygen") is not None else None,
            v2=_safe_float(row.get("v2_p_oxygen")) if row.get("v2_p_oxygen") is not None else None,
            verification_status=verification_status,
        ),
        "drug": _build_factor(
            "drug",
            v1=_safe_float(row.get("v1_p_drug")) if row.get("v1_p_drug") is not None else None,
            v2=_safe_float(row.get("v2_p_drug")) if row.get("v2_p_drug") is not None else None,
            verification_status=verification_status,
        ),
        "specialist": _build_factor(
            "specialist",
            v1=_safe_float(row.get("v1_p_specialist")) if row.get("v1_p_specialist") is not None else None,
            v2=_safe_float(row.get("v2_p_specialist")) if row.get("v2_p_specialist") is not None else None,
            verification_status=verification_status,
        ),
    }

    trust = _blended_trust(row)

    if use_cal and row.get("trust_calibrated") is not None:
        trust_calibrated = _clamp(_safe_float(row["trust_calibrated"]))
    elif _caller_trust_cal is not None:
        # Use the pre-computed calibrated trust surfaced by the upstream pipeline
        # (e.g. router passed facility dict with trust_calibrated already set).
        trust_calibrated = _clamp(_caller_trust_cal)
    else:
        trust_calibrated = trust

    extractor_reasoning = str(row.get("v1_reasoning") or "")[:2000]
    validator_reasoning = str(row.get("v2_reasoning") or "")[:2000]

    logger.info(
        "validator_result facility=%s status=%s trust=%.3f trust_cal=%.3f agreement=%s",
        facility_id, verification_status, trust, trust_calibrated, agreement,
    )

    return TrustScorerOutput(
        facility_id=facility_id,
        factors=factors,
        trust=trust,
        trust_calibrated=trust_calibrated,
        extractor_reasoning=extractor_reasoning,
        validator_reasoning=validator_reasoning,
        agreement=agreement,
    )
