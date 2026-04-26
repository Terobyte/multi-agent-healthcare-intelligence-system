import os

import pytest

import app.agents.booking as booking_module
from app.agents.booking import book_atomic


@pytest.fixture(autouse=True)
def _allow_dev_salt(monkeypatch):
    # bug #4: hash_patient_id refuses to run without explicit salt or DEV opt-in
    monkeypatch.setenv("AAROGYANET_DEV", "1")
    monkeypatch.delenv("PII_SALT", raising=False)


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
        if "FROM workspace.default.gold_trust_final" in query:
            return [("5603",)]
        if "FROM workspace.default.txn_atomic" in query and query.lstrip().startswith("SELECT"):
            return []
        if table_substr in query and "MERGE INTO" in query:
            raise RuntimeError(f"simulated {table_substr} failure")
        return None

    monkeypatch.setattr(booking_module, "warehouse_query", fake)
    r = book_atomic("5603", f"smoke_p_rb_{short_key}", {})

    assert r["status"] == "ROLLED_BACK", f"expected ROLLED_BACK, got {r}"
    assert "FAIL" in r["resources"][short_key]
    order = ["bed", "ambulance", "doctor", "drug"]
    for k in order[: order.index(short_key)]:
        assert r["resources"][k] == "OK", f"earlier resource {k} should be OK, got {r['resources'][k]}"

    # rollback compensation must actually issue UPDATE statements for each earlier-OK resource
    cancel_targets = {
        "bed": "bed_reservations", "ambulance": "ambulance_dispatches",
        "doctor": "doctor_slots", "drug": "drug_reservations",
    }
    for k in order[: order.index(short_key)]:
        table = cancel_targets[k]
        assert any(
            f"UPDATE workspace.default.{table} " in q and "status='CANCELLED'" in q
            for q, _ in call_log
        ), f"missing CANCELLED UPDATE for {table}"

    # parent must be rolled back exactly once
    assert sum(
        1 for q, _ in call_log
        if "UPDATE workspace.default.txn_atomic" in q and "status='ROLLED_BACK'" in q
    ) == 1


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
    # commit_error must be surfaced as a top-level field, NOT inside resources dict
    assert r.get("commit_error") is not None and "simulated parent" in r["commit_error"]
    assert "_commit_update_failed" not in r["resources"]
    # the rollback's failure_reason must be the actual commit error, not the placeholder
    assert "simulated parent" in r["reason"]
    # all 4 child inserts had succeeded before parent UPDATE failure
    for short in ("bed", "ambulance", "doctor", "drug"):
        assert r["resources"][short] == "OK"


def test_committed_path_has_commit_error_none(monkeypatch):
    """Every book_atomic return path must include commit_error so callers can do
    r['commit_error'] without KeyError (BookingOutput defaults handle the API edge,
    but internal Python callers don't go through Pydantic)."""
    def fake(query, params=None, _retries=1):
        if "FROM workspace.default.gold_trust_final" in query:
            return [("5603",)]
        if "FROM workspace.default.txn_atomic" in query and query.lstrip().startswith("SELECT"):
            return []
        return None

    monkeypatch.setattr(booking_module, "warehouse_query", fake)
    r = book_atomic("5603", "smoke_p_committed_shape", {})
    assert r["status"] == "COMMITTED"
    assert "commit_error" in r and r["commit_error"] is None


def test_all_return_dicts_validate_against_booking_output_schema(monkeypatch):
    """Catch ResponseValidationError at unit-test time, not at /book runtime."""
    from app.schemas import BookingOutput

    scenarios = [
        ("5603", "smoke_phantom", lambda q, p=None, _retries=1:
            [] if "gold_trust_final" in q else None),
        ("5603", "smoke_dup", lambda q, p=None, _retries=1:
            [("5603",)] if "gold_trust_final" in q
            else [("existing-txn",)] if "txn_atomic" in q and q.lstrip().startswith("SELECT")
            else None),
        # COMMITTED happy path — every child MERGE + parent UPDATE succeeds
        ("5603", "smoke_committed", lambda q, p=None, _retries=1:
            [("5603",)] if "gold_trust_final" in q
            else [] if "txn_atomic" in q and q.lstrip().startswith("SELECT")
            else None),
    ]
    for fac, pat, fake in scenarios:
        monkeypatch.setattr(booking_module, "warehouse_query", fake)
        r = book_atomic(fac, pat, {})
        BookingOutput(**r)  # raises ValidationError if shape wrong


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


def test_parent_insert_failure_returns_rejected(monkeypatch):
    """Warehouse-down at parent INSERT — must REJECT cleanly, no leaked exception text."""
    def fake(query, params=None, _retries=1):
        if "FROM workspace.default.gold_trust_final" in query:
            return [("5603",)]
        if "FROM workspace.default.txn_atomic" in query and query.lstrip().startswith("SELECT"):
            return []
        if query.lstrip().startswith("INSERT INTO workspace.default.txn_atomic"):
            raise RuntimeError("simulated cold-start: warehouse not running")
        return None

    monkeypatch.setattr(booking_module, "warehouse_query", fake)
    r = book_atomic("5603", "smoke_p_parent_fail", {})
    assert r["status"] == "REJECTED"
    assert r["transaction_id"] is None
    # reason must NOT leak the raw exception text (which could include warehouse host / token hints)
    assert "simulated cold-start" not in r["reason"]
    assert r["reason"] == "parent insert failed"


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
