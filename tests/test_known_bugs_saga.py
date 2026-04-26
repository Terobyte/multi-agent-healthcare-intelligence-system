"""Regression locks for confirmed bugs in the booking + auth layer.

Each test below intentionally FAILS on the current code so that committing it
locks in the regression. See bugs.md for the canonical list. When a bug is
fixed, the corresponding test must flip from RED to GREEN.

Bugs covered:
  - #1   DEMO_KEY auth open by default when env unset
  - #3   hash_patient_id not called in /book before INSERT
  - #4   PII salt fallback used silently when PII_SALT unset
  - #6   race condition on duplicate-active-txn check
  - #20  exc_info=True may leak Databricks token in stack trace
"""
import importlib
import logging
import re
import threading
import time
import traceback

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def _allow_dev_salt(monkeypatch):
    # Most tests don't care about PII_SALT. Bug #1 and #4 explicitly override
    # this within the test body via monkeypatch.delenv.
    monkeypatch.setenv("AAROGYANET_DEV", "1")


# --------------------------------------------------------------------------- #
# BUG #1 — DEMO_KEY auth open by default                                      #
# --------------------------------------------------------------------------- #
# app/main.py:58 uses `if DEMO_KEY and x_demo_key != DEMO_KEY: raise`. When
# DEMO_KEY env is unset (== ""), the guard short-circuits → /book is open to
# the world. Production must fail closed.
def test_bug1_demo_key_unset_must_reject_unauthenticated_post(monkeypatch):
    monkeypatch.delenv("DEMO_KEY", raising=False)
    monkeypatch.delenv("AAROGYANET_DEV", raising=False)  # production-like
    import app.main as main_module
    importlib.reload(main_module)

    monkeypatch.setattr(
        main_module, "book_atomic",
        lambda f, p, _: {"transaction_id": "uuid", "status": "COMMITTED",
                         "resources": {"bed": "OK", "ambulance": "OK",
                                       "doctor": "OK", "drug": "OK"},
                         "facility_id": f, "commit_error": None},
    )

    client = TestClient(main_module.app)
    r = client.post("/book", json={"facility_id": "5603", "patient_id": "p_anon"})

    assert r.status_code == 401, (
        f"DEMO_KEY unset must fail closed (401), got {r.status_code}: {r.text}"
    )


# --------------------------------------------------------------------------- #
# BUG #3 — hash_patient_id not called in /book before INSERT                  #
# --------------------------------------------------------------------------- #
# app/agents/booking.py — book_atomic passes raw patient_id straight into
# INSERT/MERGE params. Block 35d requires hashing first (DPDP Act 2023).
def test_bug3_raw_patient_id_must_not_reach_warehouse_params(monkeypatch):
    import app.agents.booking as booking_module

    captured: list[list] = []

    def fake(query, params=None, _retries=1):
        captured.append(list(params or []))
        if "FROM workspace.default.gold_trust_final" in query:
            return [("5603",)]
        if "FROM workspace.default.txn_atomic" in query and query.lstrip().startswith("SELECT"):
            return []
        return None

    monkeypatch.setattr(booking_module, "warehouse_query", fake)
    booking_module.book_atomic("5603", "raw_aadhaar_xxx", {})

    flat = [str(p) for params in captured for p in params]

    assert not any("raw_aadhaar_xxx" in s for s in flat), (
        f"raw patient_id leaked into warehouse params: {flat}"
    )

    hash_re = re.compile(r"^p_[0-9a-f]{16}$")
    assert any(hash_re.match(s) for s in flat), (
        f"no hashed patient_id (p_<16 hex>) found in warehouse params: {flat}"
    )


# --------------------------------------------------------------------------- #
# BUG #4 — PII salt fallback used silently when PII_SALT unset                #
# --------------------------------------------------------------------------- #
# app/util.py:15 — `_SALT = os.getenv("PII_SALT", "aarogyanet-dev-salt-...")`.
# Production must refuse to hash with the dev salt unless AAROGYANET_DEV=1.
def test_bug4_dev_salt_must_not_be_used_silently(monkeypatch):
    monkeypatch.delenv("PII_SALT", raising=False)
    monkeypatch.delenv("AAROGYANET_DEV", raising=False)

    import app.util as util_module
    importlib.reload(util_module)

    with pytest.raises(RuntimeError):
        util_module.hash_patient_id("x")


# --------------------------------------------------------------------------- #
# BUG #6 — race condition on duplicate-active-txn check                       #
# --------------------------------------------------------------------------- #
# app/agents/booking.py:38-56 — SELECT then INSERT, no atomic guard. Two
# concurrent calls for the same patient both see "no active txn" and both
# proceed to commit, double-booking the patient.
def test_bug6_concurrent_book_atomic_must_not_double_commit(monkeypatch):
    import app.agents.booking as booking_module

    state_lock = threading.Lock()
    active_txns: list[tuple[str, str, str]] = []  # (patient_id, txn_id, status)

    def fake(query, params=None, _retries=1):
        if "FROM workspace.default.gold_trust_final" in query:
            return [("5603",)]
        if "FROM workspace.default.txn_atomic" in query and query.lstrip().startswith("SELECT"):
            # Snapshot under lock, sleep AFTER releasing — both threads must
            # observe an empty SELECT before either INSERT lands.
            with state_lock:
                pat = params[0] if params else None
                snapshot = [
                    (p, txn) for p, txn, status in active_txns
                    if p == pat and status in ("RESERVED", "COMMITTED")
                ]
            time.sleep(0.1)  # widen race window outside the lock
            return [(snapshot[0][1],)] if snapshot else []
        if query.lstrip().startswith("INSERT INTO workspace.default.txn_atomic"):
            with state_lock:
                # params order: [txn_id, patient_id, facility_id]
                active_txns.append((params[1], params[0], "RESERVED"))
            return None
        if "UPDATE workspace.default.txn_atomic" in query and "status='COMMITTED'" in query:
            with state_lock:
                txn_id = params[0]
                for i, (p, t, s) in enumerate(active_txns):
                    if t == txn_id:
                        active_txns[i] = (p, t, "COMMITTED")
            return None
        return None

    monkeypatch.setattr(booking_module, "warehouse_query", fake)

    results: list[dict] = []
    results_lock = threading.Lock()
    barrier = threading.Barrier(2)

    def worker():
        # Sync both threads at the entry so they call book_atomic
        # near-simultaneously — maximises race-window overlap.
        barrier.wait()
        r = booking_module.book_atomic("5603", "race_pat", {})
        with results_lock:
            results.append(r)

    t1 = threading.Thread(target=worker)
    t2 = threading.Thread(target=worker)
    t1.start(); t2.start()
    t1.join(); t2.join()

    statuses = sorted(r["status"] for r in results)
    committed = [r for r in results if r["status"] == "COMMITTED"]

    assert len(committed) == 1, (
        f"race: expected exactly 1 COMMITTED, got {len(committed)}; "
        f"statuses={statuses}; results={results}"
    )
    # The other call must be REJECTED (or ROLLED_BACK from the dedup arm).
    assert any(r["status"] in ("REJECTED", "ROLLED_BACK") for r in results), (
        f"race: expected the loser to REJECT/ROLLED_BACK; statuses={statuses}"
    )


# --------------------------------------------------------------------------- #
# BUG #20 — exc_info=True may leak Databricks token in stack trace            #
# --------------------------------------------------------------------------- #
# app/main.py:135 — `logger.exception(...)` emits the full exception chain.
# If the underlying exception text contains a Databricks bearer token
# (databricks-sql-connector sometimes raises with the connection URL/header
# embedded), the token is dumped verbatim into log aggregators.
#
# NOTE: pytest's caplog cannot be used — main.py sets propagate=False on the
# "app" logger so caplog (root) never sees the records. We attach our own
# capture handler directly to the named loggers.
def test_bug20_exception_log_must_not_leak_databricks_token(monkeypatch):
    monkeypatch.setenv("DEMO_KEY", "test-secret")
    import app.main as main_module
    importlib.reload(main_module)

    def boom(*a, **kw):
        raise RuntimeError(
            "Bearer dapixxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx connection failed"
        )

    monkeypatch.setattr(main_module, "book_atomic", boom)

    captured: list[logging.LogRecord] = []

    class ListHandler(logging.Handler):
        def emit(self, record):
            captured.append(record)

    handler = ListHandler(level=logging.DEBUG)
    targets = [logging.getLogger("app"), logging.getLogger("app.main")]
    for lg in targets:
        lg.addHandler(handler)
        lg.setLevel(logging.DEBUG)

    try:
        client = TestClient(main_module.app)
        r = client.post(
            "/book",
            json={"facility_id": "5603", "patient_id": "p_leak"},
            headers={"X-Demo-Key": "test-secret"},
        )
    finally:
        for lg in targets:
            lg.removeHandler(handler)

    assert r.status_code == 200, r.text
    assert captured, "expected logger.exception to fire from /book"

    leaked: list[str] = []
    for rec in captured:
        rendered = rec.getMessage()
        if rec.exc_info:
            rendered += "\n" + "".join(traceback.format_exception(*rec.exc_info))
        if "dapi" in rendered:
            leaked.append(rendered)

    assert not leaked, (
        "Databricks token substring 'dapi' leaked into logger output via "
        f"logger.exception; offending records:\n{leaked}"
    )

    # Cleanup: undo DEMO_KEY for sibling tests.
    monkeypatch.delenv("DEMO_KEY", raising=False)
    importlib.reload(main_module)
