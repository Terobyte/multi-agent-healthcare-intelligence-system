"""Independent regression-sweep edge cases for previously-claimed-fixed bugs.

The locks in `test_known_bugs_saga.py` and `test_known_bugs_sse.py` cover the
core fix path for bugs #1, #3, #4, #6, #20. This file adds ONE harder edge case
chosen by an independent reviewer pass: a high-concurrency stress test of the
bug #6 per-patient lock.

Why this edge case:
  - The existing bug #6 lock spawns only 2 threads. With Python's GIL and the
    cheap fake `warehouse_query`, two threads barely interleave. A correct
    in-process lock survives 2-way contention trivially even WITHOUT the lock
    on some scheduler timings.
  - Real Render traffic during demo can have N concurrent /book POSTs on the
    same patient_id (judge mashes the demo button, browser retries, etc.). If
    `_patient_lock` ever regresses to a non-reentrant or non-per-key impl
    (e.g. someone refactors to a single global lock and forgets the per-patient
    invariant, or accidentally creates a fresh lock per call by losing the
    `_patient_locks` dict), N-way contention is far more likely to expose it
    than 2-way.

Locks in: 10 concurrent book_atomic calls for the SAME patient_id must produce
exactly 1 COMMITTED and 9 REJECTED-with-active-txn-reason. Anything else
(>1 COMMITTED, or REJECTED for the wrong reason) means the lock regressed.
"""
import threading
import time

import pytest


def test_bug6_ten_concurrent_calls_same_patient_only_one_commits(monkeypatch):
    """Stress the per-patient lock with 10 concurrent calls on one patient.

    Asserts:
      - Exactly 1 transaction reaches COMMITTED.
      - The other 9 are REJECTED with reason mentioning 'active txn'
        (i.e. they took the dedup arm AFTER the winner held the lock and
        inserted its parent row — proving the lock serialized them).
      - No call produces an unexpected status (ROLLED_BACK from a phantom
        race, or COMMITTED twice).
    """
    monkeypatch.setenv("AAROGYANET_DEV", "1")  # allow dev salt for hash_patient_id
    import app.agents.booking as booking_module

    state_lock = threading.Lock()
    active_txns: list[tuple[str, str, str]] = []  # (patient_id, txn_id, status)

    def fake(query, params=None, _retries=1):
        if "FROM workspace.default.gold_trust_final" in query:
            return [("5603",)]
        if "FROM workspace.default.txn_atomic" in query and query.lstrip().startswith("SELECT"):
            with state_lock:
                pat = params[0] if params else None
                snapshot = [
                    (p, txn) for p, txn, status in active_txns
                    if p == pat and status in ("RESERVED", "COMMITTED")
                ]
            # Sleep OUTSIDE the lock to widen the race window — any thread
            # not holding the per-patient app lock will read stale state.
            time.sleep(0.05)
            return [(snapshot[0][1],)] if snapshot else []
        if query.lstrip().startswith("INSERT INTO workspace.default.txn_atomic"):
            with state_lock:
                # params order: [txn_id, patient_id, facility_id]
                active_txns.append((params[1], params[0], "RESERVED"))
            return None
        if "MERGE INTO" in query:
            return None  # all child resources succeed
        if "UPDATE workspace.default.txn_atomic" in query and "status='COMMITTED'" in query:
            with state_lock:
                txn_id = params[0]
                for i, (p, t, s) in enumerate(active_txns):
                    if t == txn_id:
                        active_txns[i] = (p, t, "COMMITTED")
            return None
        return None

    monkeypatch.setattr(booking_module, "warehouse_query", fake)

    N = 10
    results: list[dict] = []
    results_lock = threading.Lock()
    barrier = threading.Barrier(N)

    def worker():
        barrier.wait()  # release all threads simultaneously
        r = booking_module.book_atomic("5603", "stress_pat", {})
        with results_lock:
            results.append(r)

    threads = [threading.Thread(target=worker) for _ in range(N)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(results) == N, f"expected {N} results, got {len(results)}"

    committed = [r for r in results if r["status"] == "COMMITTED"]
    rejected = [r for r in results if r["status"] == "REJECTED"]
    other = [r for r in results if r["status"] not in ("COMMITTED", "REJECTED")]

    assert len(committed) == 1, (
        f"per-patient lock failure: expected exactly 1 COMMITTED out of {N} "
        f"concurrent calls, got {len(committed)}. statuses="
        f"{sorted(r['status'] for r in results)}"
    )
    assert len(rejected) == N - 1, (
        f"expected {N - 1} REJECTED (dedup arm), got {len(rejected)}. "
        f"statuses={sorted(r['status'] for r in results)}"
    )
    assert not other, (
        f"unexpected non-COMMITTED/non-REJECTED status in stress run: {other}"
    )

    # Every loser must have hit the active-txn dedup arm, NOT some other
    # rejection (phantom facility, parent insert failed, etc.). That's the
    # signature of "the lock serialized me, then the dedup SELECT correctly
    # saw the winner's RESERVED row".
    bad_reasons = [
        r for r in rejected if "active txn" not in (r.get("reason") or "")
    ]
    assert not bad_reasons, (
        f"loser threads must reject via dedup arm ('active txn' reason), but "
        f"some rejected for other reasons: {bad_reasons}"
    )
