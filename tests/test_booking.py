import os

import pytest

import app.agents.booking as booking_module
from app.agents.booking import book_atomic


# Live-warehouse tests — opt-in via env so unit-test default doesn't dirty Delta.
LIVE = os.getenv("BOOKING_LIVE_TESTS") == "1"

requires_live = pytest.mark.skipif(
    not LIVE, reason="set BOOKING_LIVE_TESTS=1 to run against the real warehouse",
)


@requires_live
def test_happy_path_commits():
    r = book_atomic("5603", "smoke_p_happy", {})
    assert r["status"] == "COMMITTED", f"expected COMMITTED, got {r}"
    assert all(v == "OK" for v in r["resources"].values()), f"resources not all OK: {r['resources']}"
    assert r["transaction_id"] is not None


@requires_live
def test_phantom_facility_rejected():
    r = book_atomic("ghost_999", "smoke_p_phantom", {})
    assert r["status"] == "REJECTED"
    assert "not in gold_trust_final" in r["reason"]
    assert r["transaction_id"] is None


# Monkeypatched rollback tests — pure unit tests, no warehouse.
# Each parametrize covers one arm of the saga; together they hit every compensation branch.

@pytest.mark.parametrize("table_substr,short_key", [
    ("bed_reservations",     "bed"),
    ("ambulance_dispatches", "ambulance"),
    ("doctor_slots",         "doctor"),
    ("drug_reservations",    "drug"),
])
def test_resource_fail_rolls_back(monkeypatch, table_substr, short_key):
    """Simulate failure of one resource MERGE — saga must ROLLBACK and cancel earlier OKs."""
    call_log: list[tuple[str, list]] = []

    def fake(query, params=None, _retries=1):
        call_log.append((query, params or []))
        # facility existence check → return a row so saga proceeds
        if "FROM workspace.default.gold_trust_final" in query:
            return [("5603",)]
        # duplicate-active-txn check → no active txn
        if "FROM workspace.default.txn_atomic" in query and query.lstrip().startswith("SELECT"):
            return []
        # the targeted resource MERGE → raise
        if table_substr in query and "MERGE INTO" in query:
            raise RuntimeError(f"simulated {table_substr} failure")
        # everything else (parent INSERT, parent UPDATE, child UPDATE, other MERGEs) → succeed
        return None

    monkeypatch.setattr(booking_module, "warehouse_query", fake)
    r = book_atomic("5603", f"smoke_p_rb_{short_key}", {})

    assert r["status"] == "ROLLED_BACK", f"expected ROLLED_BACK, got {r}"
    assert "FAIL" in r["resources"][short_key]
    # all resources scheduled BEFORE the failing one must be OK
    order = ["bed", "ambulance", "doctor", "drug"]
    for k in order[: order.index(short_key)]:
        assert r["resources"][k] == "OK", f"earlier resource {k} should be OK, got {r['resources'][k]}"


def test_parent_commit_update_failure_triggers_child_cancel(monkeypatch):
    """Block 23 fallthrough: all 4 children OK, but parent UPDATE='COMMITTED' fails →
    saga must roll back instead of leaving inconsistency."""

    def fake(query, params=None, _retries=1):
        if "FROM workspace.default.gold_trust_final" in query:
            return [("5603",)]
        if "FROM workspace.default.txn_atomic" in query and query.lstrip().startswith("SELECT"):
            return []
        # the COMMITTED-update is the only thing that fails
        if "UPDATE workspace.default.txn_atomic" in query and "status='COMMITTED'" in query:
            raise RuntimeError("simulated parent COMMITTED update failure")
        return None

    monkeypatch.setattr(booking_module, "warehouse_query", fake)
    r = book_atomic("5603", "smoke_p_commit_fail", {})

    assert r["status"] == "ROLLED_BACK"
    assert "_commit_update_failed" in r["resources"]
    # all 4 child inserts had succeeded before parent UPDATE failure
    for short in ("bed", "ambulance", "doctor", "drug"):
        assert r["resources"][short] == "OK"


def test_phantom_facility_rejected_unit(monkeypatch):
    """Phantom facility check without warehouse — pure unit."""
    def fake(query, params=None, _retries=1):
        if "FROM workspace.default.gold_trust_final" in query:
            return []  # no row for ghost facility
        return None

    monkeypatch.setattr(booking_module, "warehouse_query", fake)
    r = book_atomic("ghost_999", "smoke_p_unit_phantom", {})
    assert r["status"] == "REJECTED"
    assert r["transaction_id"] is None
    assert "not in gold_trust_final" in r["reason"]


def test_duplicate_active_txn_rejected_unit(monkeypatch):
    def fake(query, params=None, _retries=1):
        if "FROM workspace.default.gold_trust_final" in query:
            return [("5603",)]
        if "FROM workspace.default.txn_atomic" in query and query.lstrip().startswith("SELECT"):
            return [("existing-txn-uuid",)]
        return None

    monkeypatch.setattr(booking_module, "warehouse_query", fake)
    r = book_atomic("5603", "smoke_p_dupe", {})
    assert r["status"] == "REJECTED"
    assert r["transaction_id"] == "existing-txn-uuid"
    assert "has active txn" in r["reason"]
