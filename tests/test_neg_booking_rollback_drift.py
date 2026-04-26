"""Negative test: rollback path silently swallows its own failure.

book_atomic (app/agents/booking.py ~lines 160-183) does:

    try:
        warehouse_query("UPDATE ... SET status='ROLLED_BACK' ...")
    except Exception:
        logger.exception("rollback_parent_update_failed txn=%s", txn_id)

If the rollback UPDATE itself fails, the exception is logged-and-swallowed.
The function then returns status="ROLLED_BACK" with commit_error=None,
even though the parent row in txn_atomic is still RESERVED in the warehouse.
This is a silent state-drift between reported status and actual DB state —
downstream callers (the /book API, the UI) believe the saga compensated when
it didn't, so the orphaned RESERVED row stays forever.

This test must FAIL until book_atomic distinguishes "rollback succeeded" from
"rollback ITSELF failed" (e.g. status="ROLLBACK_FAILED" / "INCONSISTENT", or
non-empty commit_error containing the rollback exception).
"""
import pytest

import app.agents.booking as booking_module
from app.agents.booking import book_atomic


@pytest.fixture(autouse=True)
def _allow_dev_salt(monkeypatch):
    # bug #4: hash_patient_id refuses without explicit salt or DEV opt-in
    monkeypatch.setenv("AAROGYANET_DEV", "1")
    monkeypatch.delenv("PII_SALT", raising=False)


def test_rollback_failure_must_not_be_reported_as_clean_rolled_back(monkeypatch):
    """Scenario:
      1. parent INSERT into txn_atomic — OK
      2. first child MERGE (bed_reservations) — OK
      3. second child MERGE (ambulance_dispatches) — RAISES (triggers rollback)
      4. rollback UPDATE of txn_atomic to ROLLED_BACK — ALSO RAISES

    Current code logs the rollback exception and falls through, returning
    status="ROLLED_BACK". That's a lie: the parent row is still RESERVED.
    """
    call_log: list[tuple[str, list]] = []

    def fake(query, params=None, _retries=1):
        call_log.append((query, list(params or [])))
        # facility lookup: facility exists
        if "FROM workspace.default.gold_trust_final" in query:
            return [("5603",)]
        # duplicate-active-txn check: none exists
        if (
            "FROM workspace.default.txn_atomic" in query
            and query.lstrip().startswith("SELECT")
        ):
            return []
        # parent INSERT — succeeds
        if query.lstrip().startswith("INSERT INTO workspace.default.txn_atomic"):
            return None
        # first child (bed_reservations) MERGE — succeeds (returns None)
        if "MERGE INTO workspace.default.bed_reservations" in query:
            return None
        # second child (ambulance_dispatches) MERGE — fails, triggers rollback
        if "MERGE INTO workspace.default.ambulance_dispatches" in query:
            raise RuntimeError("simulated ambulance MERGE failure")
        # rollback parent UPDATE itself fails
        if (
            "UPDATE workspace.default.txn_atomic" in query
            and "status='ROLLED_BACK'" in query
        ):
            raise RuntimeError("simulated rollback parent UPDATE failure")
        # any other UPDATE (child cancellations) — pretend they succeed
        return None

    monkeypatch.setattr(booking_module, "warehouse_query", fake)

    r = book_atomic("5603", "smoke_p_rollback_drift", {})

    # Sanity: we exercised the path we intended.
    assert any(
        "MERGE INTO workspace.default.ambulance_dispatches" in q for q, _ in call_log
    ), f"test setup wrong — ambulance MERGE never invoked. call_log={call_log}"
    assert any(
        "UPDATE workspace.default.txn_atomic" in q and "status='ROLLED_BACK'" in q
        for q, _ in call_log
    ), f"test setup wrong — rollback parent UPDATE never attempted. call_log={call_log}"

    # The actual claim under test:
    # the function MUST NOT report a clean "ROLLED_BACK" when the rollback
    # UPDATE itself blew up. Either the status must signal the failure, or
    # commit_error must surface the rollback exception text.
    rollback_exc_surfaced = bool(r.get("commit_error")) and "rollback" in (
        r.get("commit_error") or ""
    ).lower()
    status_signals_failure = r["status"] in (
        "ROLLBACK_FAILED",
        "INCONSISTENT",
        "ERROR",
    )

    assert status_signals_failure or rollback_exc_surfaced, (
        "rollback drift bug: parent UPDATE='ROLLED_BACK' failed during compensation, "
        "but book_atomic returned a clean ROLLED_BACK with no commit_error. "
        "DB still has the parent row as RESERVED — reported status disagrees "
        "with warehouse state. "
        f"got status={r['status']!r}, commit_error={r.get('commit_error')!r}, "
        f"reason={r.get('reason')!r}"
    )
