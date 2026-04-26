"""RouterAgent — ranks hospital candidates by trust × bed-availability × specialty match.

Stack: Python + SQL over workspace.default.gold_trust_final via databricks-sql-connector.
No Genie Code in this path — Genie Code is Layer 4 stretch only; pandas/SQL is the
reliable primary for a 24-hour hackathon window.

Ranking formula (composite score):
    score = trust_score × p_bed_final × specialty_match × distance_decay

    p_bed_final:     live prediction p_bed from TrustScorer when supplied;
                     gold p_bed column otherwise.
    specialty_match: keyword-overlap score [0.1, 1.0].
    distance_decay:  1 / (1 + travel_min / 60) — penalises far hospitals without
                     zeroing them out, so a nearby average hospital beats a distant
                     excellent one at the margin.

On any DB error (timeout, auth, query failure) the agent logs the exception and
returns an empty ranked list so the supervisor SSE stream always terminates cleanly
with a partial result rather than a 500.
"""
import logging
import math
import re
from typing import Optional
from uuid import uuid4

from app.db import warehouse_query
from contracts.schemas import (
    BedPrediction,
    RankedHospital,
    RouterInput,
    RouterOutput,
)

logger = logging.getLogger("router")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_TOP_N_DEFAULT = 5

# Hospitals with a calibrated trust score below this floor are excluded from
# the ranked list.  Keeps synthetic / post-arc-penalised rows (e.g. facility
# 8888, trust_calibrated≈0.1) from appearing in demo results while retaining
# borderline hospitals like 959 (trust_calibrated=0.35) at the bottom.
_TRUST_FLOOR = 0.3

# Haversine speed assumption for travel_min estimation.
# 1.3× road-detour factor converts straight-line km to approximate road distance.
_AVG_SPEED_KMH = 40.0
_DETOUR_FACTOR = 1.3

# Latitude / longitude lookup for major Indian cities used as the patient's
# routing origin. Falls back to the geographic centre of India for unrecognised
# city names rather than raising so the agent remains runnable offline.
_CITY_COORDS: dict[str, tuple[float, float]] = {
    "mumbai": (19.076, 72.877),
    "delhi": (28.704, 77.102),
    "new delhi": (28.613, 77.209),
    "bangalore": (12.972, 77.594),
    "bengaluru": (12.972, 77.594),
    "hyderabad": (17.385, 78.487),
    "ahmedabad": (23.023, 72.572),
    "chennai": (13.083, 80.270),
    "kolkata": (22.573, 88.364),
    "surat": (21.170, 72.832),
    "pune": (18.520, 73.856),
    "jaipur": (26.912, 75.787),
    "lucknow": (26.847, 80.947),
    "patna": (25.594, 85.137),
    "nagpur": (21.146, 79.088),
    "bhopal": (23.259, 77.413),
    "indore": (22.719, 75.857),
    "chandigarh": (30.733, 76.779),
    "coimbatore": (11.017, 76.956),
    "kochi": (9.931, 76.267),
    "visakhapatnam": (17.686, 83.218),
    "bhubaneswar": (20.296, 85.824),
    "guwahati": (26.145, 91.735),
    "thiruvananthapuram": (8.524, 76.936),
    "raipur": (21.250, 81.630),
}
_INDIA_CENTER: tuple[float, float] = (22.351, 78.668)

# City → state mapping used by the state-level fallback in _fetch_candidates.
# Keeps the same canonical keys as _CITY_COORDS so both dicts stay in sync.
_CITY_TO_STATE: dict[str, str] = {
    "mumbai": "Maharashtra",
    "delhi": "Delhi",
    "new delhi": "Delhi",
    "bangalore": "Karnataka",
    "bengaluru": "Karnataka",
    "hyderabad": "Telangana",
    "ahmedabad": "Gujarat",
    "chennai": "Tamil Nadu",
    "kolkata": "West Bengal",
    "surat": "Gujarat",
    "pune": "Maharashtra",
    "jaipur": "Rajasthan",
    "lucknow": "Uttar Pradesh",
    "patna": "Bihar",
    "nagpur": "Maharashtra",
    "bhopal": "Madhya Pradesh",
    "indore": "Madhya Pradesh",
    "chandigarh": "Punjab",
    "coimbatore": "Tamil Nadu",
    "kochi": "Kerala",
    "visakhapatnam": "Andhra Pradesh",
    "bhubaneswar": "Odisha",
    "guwahati": "Assam",
    "thiruvananthapuram": "Kerala",
    "raipur": "Chhattisgarh",
}

# Specialty synonym groups. Any keyword in the group matching the hospital's
# specialties array counts as a hit towards the specialty_match score.
_SPECIALTY_KEYWORDS: dict[str, list[str]] = {
    "cardiology": ["cardio", "heart", "cardiac", "coronary"],
    "orthopedics": ["ortho", "bone", "joint", "fracture"],
    "neurology": ["neuro", "brain", "spine", "neural"],
    "oncology": ["onco", "cancer", "tumor", "tumour"],
    "pediatrics": ["pediatr", "paediatr", "child", "neonat"],
    "gynecology": ["gynec", "gynaec", "obstet", "maternity", "pregn"],
    "general medicine": ["general", "medicine", "internal"],
    "surgery": ["surg"],
    "emergency": ["emerg", "trauma", "icu", "critical"],
    "ophthalmology": ["ophthal", "eye"],
    "dermatology": ["dermat", "skin"],
    "psychiatry": ["psych", "mental"],
    "nephrology": ["nephro", "kidney", "dialysis", "renal"],
    "gastroenterology": ["gastro", "liver", "digest"],
    "pulmonology": ["pulm", "lung", "respirat", "chest"],
}

# Cost heuristics: sorted list of (trust_threshold, base_medical_inr).
# Iterated with next() so adding a new tier only requires appending here.
_BASE_COST_BY_TRUST: list[tuple[float, int]] = [
    (0.8, 8000),   # high trust → private / major hospital
    (0.5, 4000),   # mid trust  → semi-private
    (0.0, 1500),   # low trust  → public / PHC
]
_TRAVEL_COST_INR_PER_KM = 15

# ---------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in kilometres between two lat/lon points."""
    r = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return 2.0 * r * math.asin(math.sqrt(min(a, 1.0)))


def _travel_min(distance_km: float) -> int:
    """Estimate road travel time in minutes using a detour factor + average speed."""
    road_km = distance_km * _DETOUR_FACTOR
    return max(1, round(road_km / _AVG_SPEED_KMH * 60.0))


def _city_coords(city: str) -> tuple[float, float]:
    """Return (lat, lon) for a city name; falls back to the centre of India."""
    return _CITY_COORDS.get(city.strip().lower(), _INDIA_CENTER)


# ---------------------------------------------------------------------------
# Specialty matching
# ---------------------------------------------------------------------------


def _specialty_keywords(specialty: str) -> list[str]:
    """Return the keyword set for a specialty string.

    Checks for exact dict key match first, then partial overlap against known
    synonyms, then falls back to splitting the specialty string itself so that
    unknown / free-text specialties still produce a usable keyword list.
    """
    key = specialty.strip().lower()
    if key in _SPECIALTY_KEYWORDS:
        return _SPECIALTY_KEYWORDS[key]
    for known, kws in _SPECIALTY_KEYWORDS.items():
        if key in known or any(kw in key for kw in kws):
            return kws
    return [w for w in re.split(r"\s+", key) if len(w) > 3]


def _specialty_match_score(row_specialties: object, target_specialty: str) -> float:
    """Score [0.1, 1.0] for how well a hospital's specialties match the target.

    row_specialties may be a Python list (Delta ARRAY type → list via SQL
    connector), a comma/space-joined string, a numpy array, or None.  Returning
    0.1 rather than 0.0 for no-match keeps niche-specialty hospitals in the
    candidate pool at low priority so the caller always has results.
    """
    if row_specialties is None:
        return 0.1
    try:
        empty = not row_specialties
    except ValueError:
        empty = False  # numpy array with multiple elements is non-empty
    if empty:
        return 0.1
    if isinstance(row_specialties, (list, tuple)):
        combined = " ".join(str(s) for s in row_specialties).lower()
    else:
        combined = str(row_specialties).lower()
    keywords = _specialty_keywords(target_specialty)
    if not keywords:
        return 0.5
    hits = sum(1 for kw in keywords if kw in combined)
    if hits == 0:
        return 0.1
    return min(1.0, 0.4 + 0.6 * hits / max(len(keywords), 1))


# ---------------------------------------------------------------------------
# Ranking helpers
# ---------------------------------------------------------------------------


def _distance_decay(travel_min: int) -> float:
    """Smooth decay: nearer hospitals score higher, but distant ones aren't zeroed."""
    return 1.0 / (1.0 + travel_min / 60.0)


def _composite_score(
    trust_score: float,
    p_bed: float,
    specialty_match: float,
    travel_min: int,
) -> float:
    """Multiplicative ranking signal combining all four routing factors."""
    return trust_score * p_bed * specialty_match * _distance_decay(travel_min)


def _cost_estimate(trust_score: float, distance_km: float) -> tuple[int, int]:
    """Return (medical_cost_inr, non_medical_cost_inr) rough heuristics.

    Medical cost is tiered by trust score (proxy for hospital tier).
    Non-medical cost is proportional to travel distance (ambulance + escort).
    """
    base = next(b for thresh, b in _BASE_COST_BY_TRUST if trust_score >= thresh)
    travel_cost = max(0, round(distance_km * _TRAVEL_COST_INR_PER_KM))
    return base, travel_cost


# ---------------------------------------------------------------------------
# Database layer
# ---------------------------------------------------------------------------

# Primary queries: LEFT JOIN v_trust_calibrated so that outcome-adjusted scores
# are used when available.  COALESCE means rows with no calibration entry still
# get a valid trust_effective equal to the raw trust_score — the ranking never
# breaks on a NULL.  If v_trust_calibrated doesn't exist yet (Mian's migration
# hasn't run) the whole query raises; _fetch_candidates catches that and retries
# with the simple fallback queries below.
_CITY_QUERY_CAL = """
SELECT
  g.facility_id, g.name, g.city, g.state,
  g.trust_score,
  COALESCE(tc.trust_calibrated, g.trust_score) AS trust_effective,
  g.p_bed,
  g.lat, g.lon,
  g.specialties
FROM workspace.default.gold_trust_final g
LEFT JOIN workspace.default.v_trust_calibrated tc
  ON g.facility_id = tc.facility_id
WHERE LOWER(g.city) = LOWER(?)
  AND g.trust_score > 0.0
ORDER BY trust_effective DESC
LIMIT 200
"""

_STATE_QUERY_CAL = """
SELECT
  g.facility_id, g.name, g.city, g.state,
  g.trust_score,
  COALESCE(tc.trust_calibrated, g.trust_score) AS trust_effective,
  g.p_bed,
  g.lat, g.lon,
  g.specialties
FROM workspace.default.gold_trust_final g
LEFT JOIN workspace.default.v_trust_calibrated tc
  ON g.facility_id = tc.facility_id
WHERE LOWER(g.state) = LOWER(?)
  AND g.trust_score > 0.0
ORDER BY trust_effective DESC
LIMIT 200
"""

# Simple fallback queries (no calibrated view) — used when v_trust_calibrated
# is absent.  After loading these rows, _fetch_candidates mirrors trust_score
# into trust_effective so route() always reads a single key.
_CITY_QUERY = """
SELECT
  facility_id, name, city, state,
  trust_score, p_bed,
  lat, lon,
  specialties
FROM workspace.default.gold_trust_final
WHERE LOWER(city) = LOWER(?)
  AND trust_score > 0.0
ORDER BY trust_score DESC
LIMIT 200
"""

# Broader fallback: match on state when the city-exact query returns nothing.
# Tier-2 Indian cities are sometimes stored under their state name in the source
# dataset; this fallback recovers those rows without a schema change.
_STATE_QUERY = """
SELECT
  facility_id, name, city, state,
  trust_score, p_bed,
  lat, lon,
  specialties
FROM workspace.default.gold_trust_final
WHERE LOWER(state) = LOWER(?)
  AND trust_score > 0.0
ORDER BY trust_score DESC
LIMIT 200
"""

_ROW_COLS_CAL = (
    "facility_id", "name", "city", "state",
    "trust_score", "trust_effective", "p_bed", "lat", "lon", "specialties",
)

_ROW_COLS = (
    "facility_id", "name", "city", "state",
    "trust_score", "p_bed", "lat", "lon", "specialties",
)


def _fetch_candidates(city: str) -> list[dict]:
    """Query Gold for hospital rows in the target city (state as fallback).

    Strategy:
      1. Calibrated city query — LEFT JOIN v_trust_calibrated; trust_effective
         uses outcome-adjusted score when available, raw trust_score otherwise.
      2. Calibrated state query — same join, broader geo filter.
      3. Simple city/state fallback — if v_trust_calibrated doesn't exist yet,
         re-run without the join and set trust_effective = trust_score in Python.

    Returns [] on any DB error so the caller produces an empty but well-formed
    RouterOutput rather than propagating a warehouse exception through FastAPI.
    """
    rows: object = None
    use_cal = True  # track whether the calibrated path succeeded

    try:
        rows = warehouse_query(_CITY_QUERY_CAL, [city])
    except Exception:
        logger.warning("router_cal_city_query_failed city=%s — falling back to simple query", city)
        use_cal = False
        try:
            rows = warehouse_query(_CITY_QUERY, [city])
        except Exception:
            logger.exception("router_city_query_failed city=%s", city)

    if not rows:
        state = _CITY_TO_STATE.get(city.strip().lower())
        if state:
            if use_cal:
                try:
                    rows = warehouse_query(_STATE_QUERY_CAL, [state])
                except Exception:
                    logger.warning(
                        "router_cal_state_query_failed state=%s — falling back to simple query", state
                    )
                    use_cal = False
                    try:
                        rows = warehouse_query(_STATE_QUERY, [state])
                    except Exception:
                        logger.exception("router_state_query_failed state=%s", state)
            else:
                try:
                    rows = warehouse_query(_STATE_QUERY, [state])
                except Exception:
                    logger.exception("router_state_query_failed state=%s", state)
        else:
            logger.warning("router_no_state_mapping city=%s", city)

    if not rows:
        logger.warning("router_no_candidates city=%s", city)
        return []

    col_map = _ROW_COLS_CAL if use_cal else _ROW_COLS
    result = [dict(zip(col_map, row)) for row in rows]

    # When the simple (no-join) path was used, mirror trust_score → trust_effective
    # so route() can always read a single key without branching.
    if not use_cal:
        for d in result:
            d.setdefault("trust_effective", d["trust_score"])

    return result


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def route(
    inp: RouterInput,
    top_n: int = _TOP_N_DEFAULT,
    trace_id: Optional[str] = None,
) -> RouterOutput:
    """Rank hospital candidates for a triage result.

    Combines Gold trust scores, live bed predictions from TrustScorer, specialty
    keyword matching, and haversine distance into a single composite score, then
    returns the top-N hospitals.

    Args:
        inp:      RouterInput with specialty, city, and bed predictions list.
        top_n:    Maximum ranked results to return (default 5).
        trace_id: Caller-supplied trace correlation ID; generated when absent.

    Returns:
        RouterOutput with a ranked list and trace metadata.  The ranked list may
        be empty if the DB is unavailable or no hospitals match the city/state.
    """
    if trace_id is None:
        trace_id = str(uuid4())

    city_lat, city_lon = _city_coords(inp.city)
    preds: dict[str, float] = {p.hospital_id: p.p_bed for p in inp.predictions}
    candidates = _fetch_candidates(inp.city)

    scored: list[tuple[float, RankedHospital]] = []
    for row in candidates:
        fid = str(row["facility_id"])
        # trust_effective: outcome-calibrated score when v_trust_calibrated is
        # available; otherwise equals raw trust_score (_fetch_candidates ensures
        # the key is always present via setdefault).
        trust = float(row.get("trust_effective") or row.get("trust_score") or 0.0)
        if trust < _TRUST_FLOOR:
            continue  # drop low-credibility hospitals (synthetic / arc-penalised)
        gold_p_bed = float(row.get("p_bed") or 0.0)
        # Use live prediction when available; fall back to Gold column.
        p_bed = preds.get(fid, gold_p_bed)

        raw_lat = row.get("lat")
        raw_lon = row.get("lon")
        if raw_lat is None or raw_lon is None:
            # No geo data — place at city centre with a moderate travel estimate.
            h_lat, h_lon = city_lat, city_lon
            dist_km = 0.0
            t_min = 30
        else:
            h_lat, h_lon = float(raw_lat), float(raw_lon)
            dist_km = _haversine_km(city_lat, city_lon, h_lat, h_lon)
            t_min = _travel_min(dist_km)

        sp_match = _specialty_match_score(row.get("specialties"), inp.specialty)
        score = _composite_score(trust, p_bed, sp_match, t_min)
        medical_cost, non_medical_cost = _cost_estimate(trust, dist_km)

        scored.append((
            score,
            RankedHospital(
                hospital_id=fid,
                name=str(row.get("name") or fid),
                travel_min=t_min,
                specialty_match=round(sp_match, 3),
                cost_estimate_inr=medical_cost,
                non_medical_cost_inr=non_medical_cost,
                lat=h_lat,
                lon=h_lon,
                trust_calibrated=round(min(max(trust, 0.0), 1.0), 4),
            ),
        ))

    scored.sort(key=lambda x: x[0], reverse=True)
    ranked = [h for _, h in scored[:top_n]]

    logger.info(
        "router_ranked city=%s specialty=%s candidates=%d returned=%d trace=%s",
        inp.city, inp.specialty, len(candidates), len(ranked), trace_id,
    )

    return RouterOutput(
        ranked=ranked,
        genie_query_id=str(uuid4()),  # pandas/SQL path — no Genie query ID
        trace_id=trace_id,
    )


def recommend(
    triage,
    city: str = "mumbai",
    top_n: int = _TOP_N_DEFAULT,
) -> list[RankedHospital]:
    """Convenience wrapper: rank hospitals directly from a TriageOutput.

    Accepts any object with a ``.specialty`` attribute — duck-typed so both
    ``app.schemas.TriageOutput`` and ``contracts.schemas.TriageOutput`` work
    without adding a cross-module import.  Uses ``city`` as the routing
    origin when the triage result carries no location context.

    Returns the ranked list (may be empty if DB unavailable).
    """
    inp = RouterInput(specialty=triage.specialty, city=city, predictions=[])
    return route(inp, top_n=top_n).ranked
