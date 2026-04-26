"""Atomic 4-resource booking saga over the txn_atomic + 4 resource Delta tables.

Pattern: parent INSERT (RESERVED) → 4 child MERGEs → if all OK, parent UPDATE
COMMITTED; on any failure, parent UPDATE ROLLED_BACK + cancel succeeded children.

Delta has no cross-table ACID, so this is saga-style compensation. Per-table
writes are themselves ACID via Delta. See scripts/databricks/07_atomic_booking.sql.
"""
import logging
import threading
from collections import OrderedDict
from uuid import uuid4

from app.db import warehouse_query
from app.util import hash_patient_id

logger = logging.getLogger("booking")

# bug #6: in-process serialization for concurrent requests on the same patient.
# A real distributed lock (Redis/Delta unique constraint) is needed if the demo
# scales beyond one Render container.
#
# LRU-style eviction: a long-running process that sees N distinct patient_ids
# would otherwise grow this dict without bound (each key holds a Lock object +
# OrderedDict overhead). Cap it; on overflow drop the oldest entry. Worst case
# under contention is a stale lock GC'd while still held — extremely unlikely
# given the cap (10k) is far above realistic concurrent-patient counts.
_PATIENT_LOCK_LIMIT = 10000
_patient_locks: "OrderedDict[str, threading.Lock]" = OrderedDict()
_patient_locks_guard = threading.Lock()


def _patient_lock(key: str) -> threading.Lock:
    with _patient_locks_guard:
        lock = _patient_locks.get(key)
        if lock is None:
            lock = threading.Lock()
            _patient_locks[key] = lock
            # Evict oldest entries if we've grown past the cap.
            while len(_patient_locks) > _PATIENT_LOCK_LIMIT:
                _patient_locks.popitem(last=False)
        else:
            # Touch the entry so recently used keys move to the end (true LRU).
            _patient_locks.move_to_end(key)
        return lock

# (table_name, pk_column, initial_status_per_DDL_enum)
RESOURCE_TABLES = [
    ("bed_reservations",     "reservation_id", "RESERVED"),
    ("ambulance_dispatches", "dispatch_id",    "DISPATCHED"),
    ("doctor_slots",         "slot_id",        "RESERVED"),
    ("drug_reservations",    "reservation_id", "RESERVED"),
]
ALLOWED_TABLES = {t for t, _, _ in RESOURCE_TABLES}
# Derive from RESOURCE_TABLES so adding a new resource (e.g. ("oxygen_cylinders",
# ...)) automatically gets a rollback path. Hand-maintaining a parallel dict was
# a drift hazard.
RESOURCE_TABLE_BY_SHORT = {t.split("_")[0]: t for t, _, _ in RESOURCE_TABLES}
# RuntimeError, not assert — Python -O strips asserts entirely; a silent drop
# of a short key would leave orphaned RESERVED rows on rollback in production.
if set(RESOURCE_TABLE_BY_SHORT.values()) != ALLOWED_TABLES:
    raise RuntimeError(
        "RESOURCE_TABLE_BY_SHORT drifted from RESOURCE_TABLES — short keys collided. "
        "Two tables share the same first segment (e.g. bed_reservations + bed_overflow). "
        "Pick a different prefix or refactor the dict construction."
    )


def book_atomic(facility_id: str, patient_id: str, factors_required: dict) -> dict:
    # bug #3: hash patient_id at entry; raw value never reaches Delta or logs.
    hashed_pid = hash_patient_id(patient_id)
    # bug #6: serialize concurrent requests for the same patient at process level.
    with _patient_lock(hashed_pid):
        return _book_atomic_inner(facility_id, hashed_pid, factors_required)


def _book_atomic_inner(facility_id: str, hashed_pid: str, factors_required: dict) -> dict:
    # 1. facility existence — never insert a txn for a phantom facility
    rows = warehouse_query(
        "SELECT facility_id FROM workspace.default.gold_trust_final WHERE facility_id=?",
        [facility_id],
    )
    if not rows:
        return {
            "transaction_id": None, "status": "REJECTED",
            "resources": {}, "facility_id": facility_id,
            "reason": f"facility {facility_id} not in gold_trust_final",
            "commit_error": None,
        }

    # 2. duplicate active txn — don't double-saga the same patient
    active = warehouse_query(
        "SELECT transaction_id FROM workspace.default.txn_atomic "
        "WHERE patient_id=? AND status IN ('RESERVED','COMMITTED') LIMIT 1",
        [hashed_pid],
    )
    if active:
        return {
            "transaction_id": active[0][0], "status": "REJECTED",
            "resources": {}, "facility_id": facility_id,
            "reason": f"patient already has active txn {active[0][0]}",
            "commit_error": None,
        }

    # 3. parent insert (saga begin)
    txn_id = str(uuid4())
    try:
        warehouse_query(
            "INSERT INTO workspace.default.txn_atomic "
            "(transaction_id, patient_id, facility_id, status, created_ts, updated_ts) "
            "VALUES (?, ?, ?, 'RESERVED', current_timestamp(), current_timestamp())",
            [txn_id, hashed_pid, facility_id],
        )
    except Exception as e:
        # patient_id in the log is hashed (bug #3 + #20).
        logger.exception("parent_insert_failed txn=%s patient=%s", txn_id, hashed_pid)
        return {
            "transaction_id": None, "status": "REJECTED",
            "resources": {}, "facility_id": facility_id,
            "reason": "parent insert failed",
            "commit_error": None,
        }

    # 4. child inserts (MERGE used for parameterized atomic INSERT — re-running
    # an identical txn_id is a no-op because the child PK is derived
    # deterministically from (txn_id, table), so the second call's MERGE source
    # row carries the same PK and a real Delta warehouse can dedup at PK
    # granularity even if the ON-clause ever drifts off transaction_id).
    results: dict[str, str] = {}
    commit_error: str | None = None
    for table, pk_col, init_status in RESOURCE_TABLES:
        # Replaces `assert` (stripped under `python -O`) — a runtime check
        # that survives optimised builds; an unauthorised table name must
        # never be interpolated into the f-string MERGE below.
        if table not in ALLOWED_TABLES:
            raise ValueError(f"unauthorized table: {table}")
        short = table.split("_")[0]   # bed | ambulance | doctor | drug
        # Deterministic child PK from (txn_id, table). Re-running with the same
        # txn_id reproduces byte-identical params, so audit logs are stable and
        # warehouse dedup converges on the PK. The unused uuid4() preserves the
        # historical 5-call-per-book_atomic sequence (parent + 4 children) that
        # tests pin via monkeypatched generators; dropping it would shift slots.
        _ = uuid4()
        child_pk = f"{txn_id}-{table}"
        try:
            warehouse_query(
                f"MERGE INTO workspace.default.{table} t "
                f"USING (SELECT ? as transaction_id, ? as facility_id, ? as status, ? as patient_id) s "
                f"ON t.transaction_id = s.transaction_id "
                f"WHEN NOT MATCHED THEN INSERT "
                f"({pk_col}, transaction_id, facility_id, status, patient_id, created_ts, updated_ts) "
                f"VALUES (?, s.transaction_id, s.facility_id, s.status, s.patient_id, current_timestamp(), current_timestamp())",
                [txn_id, facility_id, init_status, hashed_pid, child_pk],
            )
            results[short] = "OK"
        except Exception as e:
            logger.exception("child_merge_failed txn=%s table=%s", txn_id, table)
            results[short] = f"FAIL: {str(e)[:200]}"
            break

    # 5. compensating decision
    if results and all(v == "OK" for v in results.values()) and len(results) == len(RESOURCE_TABLES):
        try:
            warehouse_query(
                "UPDATE workspace.default.txn_atomic "
                "SET status='COMMITTED', updated_ts=current_timestamp() "
                "WHERE transaction_id=?",
                [txn_id],
            )
            return {
                "transaction_id": txn_id, "status": "COMMITTED",
                "resources": results, "facility_id": facility_id,
                "commit_error": None,
            }
        except Exception as e:
            # parent UPDATE failed after children OK — fall through to rollback.
            # Keep commit_error in its own variable, NOT inside results, so the
            # downstream UI doesn't render a fake "_commit_update_failed" resource row.
            logger.exception("commit_update_failed txn=%s", txn_id)
            commit_error = str(e)[:200]

    # rollback path
    fail_reason = (
        commit_error
        or next((v for v in results.values() if v.startswith("FAIL")), "post-commit-fail")
    )[:500]
    # Track rollback-itself failures so we don't lie to callers about a clean
    # ROLLED_BACK state when the parent UPDATE compensation also blew up
    # (would leave the parent row stuck at RESERVED in the warehouse).
    final_status = "ROLLED_BACK"
    rollback_error: str | None = None
    try:
        warehouse_query(
            "UPDATE workspace.default.txn_atomic "
            "SET status='ROLLED_BACK', failure_reason=?, updated_ts=current_timestamp() "
            "WHERE transaction_id=?",
            [fail_reason, txn_id],
        )
    except Exception as e:
        logger.exception("rollback_parent_update_failed txn=%s", txn_id)
        final_status = "ROLLBACK_FAILED"
        rollback_error = f"rollback parent UPDATE failed: {str(e)[:200]}"

    for short, v in results.items():
        if v != "OK":
            continue
        table = RESOURCE_TABLE_BY_SHORT[short]
        # Same -O survival concern as the forward path above.
        if table not in ALLOWED_TABLES:
            raise ValueError(f"unauthorized table: {table}")
        try:
            warehouse_query(
                f"UPDATE workspace.default.{table} "
                f"SET status='CANCELLED', updated_ts=current_timestamp() "
                f"WHERE transaction_id=?",
                [txn_id],
            )
        except Exception as e:
            logger.exception("rollback_child_update_failed txn=%s table=%s", txn_id, table)
            if final_status == "ROLLED_BACK":
                final_status = "ROLLBACK_FAILED"
            existing = rollback_error or ""
            child_msg = f"rollback child UPDATE failed for {table}: {str(e)[:200]}"
            rollback_error = (existing + "; " + child_msg).strip("; ") if existing else child_msg

    # Surface rollback failure in commit_error so callers/UI see the drift
    # between reported status and warehouse state instead of a silent lie.
    final_commit_error: str | None = commit_error
    if rollback_error:
        final_commit_error = (
            f"{commit_error}; {rollback_error}" if commit_error else rollback_error
        )

    return {
        "transaction_id": txn_id, "status": final_status,
        "resources": results, "facility_id": facility_id,
        "reason": fail_reason,
        "commit_error": final_commit_error,
    }
