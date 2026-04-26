"""Regression tests for router.py calibrated-trust phase.

Scenario 1 — view exists, calibrated score changes ranking:
  Hospital B has a higher trust_calibrated than Hospital A despite a lower raw
  trust_score.  After the fix (ORDER BY trust_effective), B should appear first
  in RouterOutput.ranked when the calibrated path succeeds.

Scenario 2 — view missing, simple query retry still returns candidates:
  The calibrated query raises (simulating a missing v_trust_calibrated view).
  The router falls back to the simple query, and route() still returns a non-
  empty ranked list — the absence of the view never produces an empty result.

Scenario 3 — demo allowlist arc (5603, 8888, 959, 2672, 186, 881):
  All six demo hospitals are returned by the DB; the router applies the
  _TRUST_FLOOR=0.3 filter, drops 8888 (synthetic, trust_calibrated≈0.1),
  keeps the remaining five sorted by composite score (trust-dominant when
  p_bed and specialty_match are equal), and places 5603 (INHS Sanjivani,
  trust_calibrated=0.888) at rank 0.  959 (post-arc, calibrated=0.35) is
  present but ranked last among the five.
"""
import sys
from unittest.mock import patch

import pytest

# Ensure the project root is on sys.path (conftest.py does this, but be explicit)
# so the import works whether the test is run standalone or via pytest.

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_cal_row(facility_id, name, trust_score, trust_calibrated, p_bed=0.5,
                   lat=19.076, lon=72.877, specialties="cardiology"):
    """Return a tuple matching _ROW_COLS_CAL column order."""
    trust_effective = trust_calibrated if trust_calibrated is not None else trust_score
    return (facility_id, name, "Mumbai", "Maharashtra",
            trust_score, trust_effective, p_bed, lat, lon, specialties)


def _make_simple_row(facility_id, name, trust_score, p_bed=0.5,
                      lat=19.076, lon=72.877, specialties="cardiology"):
    """Return a tuple matching _ROW_COLS column order (no trust_effective)."""
    return (facility_id, name, "Mumbai", "Maharashtra",
            trust_score, p_bed, lat, lon, specialties)


def _router_input(city="Mumbai", specialty="cardiology"):
    from contracts.schemas import RouterInput
    return RouterInput(specialty=specialty, city=city, predictions=[])


# ---------------------------------------------------------------------------
# Scenario 1: calibrated view exists, calibrated score governs ranking
# ---------------------------------------------------------------------------

def test_calibrated_score_governs_ranking(monkeypatch):
    """Hospital B (lower raw trust, higher calibrated trust) ranks above A."""
    # Hospital A: high raw trust_score=0.9, calibrated stays same → trust_effective=0.9
    # Hospital B: lower raw trust_score=0.6, but calibrated=0.95 → trust_effective=0.95
    # After fix: SQL returns B first (trust_effective DESC); Python composite also sees
    # B's higher trust so B ends up ranked #1.
    row_a = _make_cal_row("hosp_a", "Alpha Hospital",
                           trust_score=0.9, trust_calibrated=0.9)
    row_b = _make_cal_row("hosp_b", "Beta Hospital",
                           trust_score=0.6, trust_calibrated=0.95)

    # SQL returns B first (simulating correct ORDER BY trust_effective DESC)
    cal_rows = [row_b, row_a]

    with patch("app.agents.router.warehouse_query", return_value=cal_rows):
        sys.modules.pop("app.agents.router", None)
        import app.agents.router as router_mod
        # Re-patch after import since we popped the module
        with patch.object(router_mod, "warehouse_query", return_value=cal_rows):
            result = router_mod.route(_router_input())

    assert len(result.ranked) >= 2, "Expected at least 2 ranked hospitals"
    assert result.ranked[0].hospital_id == "hosp_b", (
        f"Beta (calibrated=0.95) should rank above Alpha (calibrated=0.9), "
        f"got {result.ranked[0].hospital_id}"
    )


# ---------------------------------------------------------------------------
# Scenario 2: view missing, simple-query retry still returns candidates
# ---------------------------------------------------------------------------

def test_missing_view_falls_back_to_simple_query(monkeypatch):
    """When v_trust_calibrated is absent, route() still returns candidates."""
    simple_rows = [
        _make_simple_row("hosp_x", "Xray Hospital", trust_score=0.8),
        _make_simple_row("hosp_y", "Yoga Hospital", trust_score=0.7),
    ]

    call_count = {"n": 0}

    def _mock_query(sql, params):
        call_count["n"] += 1
        if "v_trust_calibrated" in sql:
            raise Exception("Table or view not found: v_trust_calibrated")
        return simple_rows

    sys.modules.pop("app.agents.router", None)
    import app.agents.router as router_mod

    with patch.object(router_mod, "warehouse_query", side_effect=_mock_query):
        result = router_mod.route(_router_input())

    assert call_count["n"] >= 2, (
        "Expected at least 2 warehouse_query calls (calibrated attempt + simple retry)"
    )
    assert len(result.ranked) > 0, (
        "route() must return candidates even when v_trust_calibrated view is missing"
    )
    # trust_effective should equal trust_score in the fallback path
    ids = {h.hospital_id for h in result.ranked}
    assert "hosp_x" in ids or "hosp_y" in ids, (
        "Expected hosp_x or hosp_y in ranked output from simple-query fallback"
    )


# ---------------------------------------------------------------------------
# Scenario 3: demo allowlist arc — trust floor filters 8888, 5603 tops list
# ---------------------------------------------------------------------------

# Canonical calibrated trust values from validate_invariants.py and the demo arc.
# All rows share the same city coordinates and p_bed so that the composite score
# is proportional to trust_effective alone, making the rank order deterministic.
_DEMO_LAT, _DEMO_LON = 19.076, 72.877  # Mumbai centroid

_DEMO_ROWS = [
    # (fid, name, city, state, trust_score, trust_effective, p_bed, lat, lon, specialties)
    ("5603", "INHS Sanjivani",      "Mumbai", "Maharashtra", 0.888, 0.888, 0.7, _DEMO_LAT, _DEMO_LON, "general medicine"),
    ("8888", "Synthetic Hospital",  "Mumbai", "Maharashtra", 0.500, 0.100, 0.7, _DEMO_LAT, _DEMO_LON, "general medicine"),
    ("959",  "Aradhna Hospital",    "Mumbai", "Maharashtra", 0.831, 0.350, 0.7, _DEMO_LAT, _DEMO_LON, "general medicine"),
    ("2672", "Delhi Liver Centre",  "Mumbai", "Maharashtra", 0.863, 0.863, 0.7, _DEMO_LAT, _DEMO_LON, "general medicine"),
    ("186",  "Aadit Eye Centre",    "Mumbai", "Maharashtra", 0.425, 0.425, 0.7, _DEMO_LAT, _DEMO_LON, "general medicine"),
    ("881",  "Apex Eye Hospital",   "Mumbai", "Maharashtra", 0.825, 0.825, 0.7, _DEMO_LAT, _DEMO_LON, "general medicine"),
]


def test_demo_allowlist_top_hospital_and_floor_filter():
    """5603 ranks first; 8888 (trust_calibrated=0.1) is dropped by _TRUST_FLOOR=0.3."""
    import app.agents.router as router_mod

    with patch.object(router_mod, "warehouse_query", return_value=_DEMO_ROWS):
        result = router_mod.route(_router_input(specialty="general medicine"))

    ranked_ids = [h.hospital_id for h in result.ranked]

    # 8888 (trust_effective=0.1) is below the 0.3 floor → must be absent
    assert "8888" not in ranked_ids, (
        f"synthetic hospital 8888 (trust_calibrated=0.1) must be filtered by "
        f"_TRUST_FLOOR=0.3; got ranked list {ranked_ids}"
    )

    # 5603 (trust_effective=0.888) must be the top result
    assert ranked_ids[0] == "5603", (
        f"5603 (INHS Sanjivani, trust_calibrated=0.888) should be ranked first; "
        f"got {ranked_ids[0]}"
    )

    # At most 5 hospitals returned from the 6-row input (8888 filtered)
    assert len(ranked_ids) <= 5, (
        f"expected at most 5 ranked hospitals, got {len(ranked_ids)}: {ranked_ids}"
    )


def test_demo_allowlist_post_arc_hospital_not_first():
    """959 (calibrated=0.35) passes the 0.3 floor but must rank below 5603."""
    import app.agents.router as router_mod

    with patch.object(router_mod, "warehouse_query", return_value=_DEMO_ROWS):
        result = router_mod.route(_router_input(specialty="general medicine"))

    ranked_ids = [h.hospital_id for h in result.ranked]

    # 959 should appear (0.35 > 0.3 floor) but not be ranked first
    assert "959" in ranked_ids, (
        "959 (trust_calibrated=0.35) is above _TRUST_FLOOR=0.3 and must be present"
    )
    assert ranked_ids.index("959") > 0, (
        f"959 (post-arc, calibrated=0.35) must not be ranked first; "
        f"got position {ranked_ids.index('959')} in {ranked_ids}"
    )
