"""Atomic 4-resource booking saga over the txn_atomic + 4 resource Delta tables.

Pattern: parent INSERT (RESERVED) → 4 child MERGEs → if all OK, parent UPDATE
COMMITTED; on any failure, parent UPDATE ROLLED_BACK + cancel succeeded children.

Delta has no cross-table ACID, so this is saga-style compensation. Per-table
writes are themselves ACID via Delta. See scripts/databricks/07_atomic_booking.sql.
"""
import logging
from uuid import uuid4

from app.db import warehouse_query

logger = logging.getLogger("booking")

# (table_name, pk_column, initial_status_per_DDL_enum)
RESOURCE_TABLES = [
    ("bed_reservations",     "reservation_id", "RESERVED"),
    ("ambulance_dispatches", "dispatch_id",    "DISPATCHED"),
    ("doctor_slots",         "slot_id",        "RESERVED"),
    ("drug_reservations",    "reservation_id", "RESERVED"),
]
ALLOWED_TABLES = {t for t, _, _ in RESOURCE_TABLES}
RESOURCE_TABLE_BY_SHORT = {
    "bed": "bed_reservations",
    "ambulance": "ambulance_dispatches",
    "doctor": "doctor_slots",
    "drug": "drug_reservations",
}


def book_atomic(facility_id: str, patient_id: str, factors_required: dict) -> dict:
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
        }

    # 2. duplicate active txn — don't double-saga the same patient
    active = warehouse_query(
        "SELECT transaction_id FROM workspace.default.txn_atomic "
        "WHERE patient_id=? AND status IN ('RESERVED','COMMITTED') LIMIT 1",
        [patient_id],
    )
    if active:
        return {
            "transaction_id": active[0][0], "status": "REJECTED",
            "resources": {}, "facility_id": facility_id,
            "reason": f"patient {patient_id} has active txn {active[0][0]}",
        }

    # 3. parent insert (saga begin)
    txn_id = str(uuid4())
    try:
        warehouse_query(
            "INSERT INTO workspace.default.txn_atomic "
            "(transaction_id, patient_id, facility_id, status, created_ts, updated_ts) "
            "VALUES (?, ?, ?, 'RESERVED', current_timestamp(), current_timestamp())",
            [txn_id, patient_id, facility_id],
        )
    except Exception as e:
        return {
            "transaction_id": None, "status": "REJECTED",
            "resources": {}, "facility_id": facility_id,
            "reason": f"parent insert failed: {e}",
        }

    # 4. child inserts (idempotent MERGE — re-running same txn_id is a no-op)
    results: dict[str, str] = {}
    for table, pk_col, init_status in RESOURCE_TABLES:
        assert table in ALLOWED_TABLES, "table allowlist guard against future user-input bugs"
        short = table.split("_")[0]   # bed | ambulance | doctor | drug
        try:
            warehouse_query(
                f"MERGE INTO workspace.default.{table} t "
                f"USING (SELECT ? as transaction_id, ? as facility_id, ? as status, ? as patient_id) s "
                f"ON t.transaction_id = s.transaction_id "
                f"WHEN NOT MATCHED THEN INSERT "
                f"({pk_col}, transaction_id, facility_id, status, patient_id, created_ts, updated_ts) "
                f"VALUES (?, s.transaction_id, s.facility_id, s.status, s.patient_id, current_timestamp(), current_timestamp())",
                [txn_id, facility_id, init_status, patient_id, str(uuid4())],
            )
            results[short] = "OK"
        except Exception as e:
            results[short] = f"FAIL: {str(e)[:200]}"
            break

    # 5. compensating decision
    if all(v == "OK" for v in results.values()):
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
            }
        except Exception as e:
            # parent UPDATE failed after children OK — fall through to rollback
            logger.error("commit_update_failed txn=%s err=%s", txn_id, e)
            results["_commit_update_failed"] = str(e)[:200]

    # rollback path
    fail_reason = next(
        (v for v in results.values() if v.startswith("FAIL")),
        "post-commit-fail",
    )[:500]
    try:
        warehouse_query(
            "UPDATE workspace.default.txn_atomic "
            "SET status='ROLLED_BACK', failure_reason=?, updated_ts=current_timestamp() "
            "WHERE transaction_id=?",
            [fail_reason, txn_id],
        )
    except Exception as e:
        logger.error("rollback_parent_update_failed txn=%s err=%s", txn_id, e)

    for short, v in results.items():
        if short.startswith("_") or v != "OK":
            continue
        table = RESOURCE_TABLE_BY_SHORT[short]
        assert table in {"bed_reservations", "ambulance_dispatches", "doctor_slots", "drug_reservations"}
        try:
            warehouse_query(
                f"UPDATE workspace.default.{table} "
                f"SET status='CANCELLED', updated_ts=current_timestamp() "
                f"WHERE transaction_id=?",
                [txn_id],
            )
        except Exception as e:
            logger.error("rollback_child_update_failed txn=%s table=%s err=%s", txn_id, table, e)

    return {
        "transaction_id": txn_id, "status": "ROLLED_BACK",
        "resources": results, "facility_id": facility_id,
        "reason": fail_reason,
    }
