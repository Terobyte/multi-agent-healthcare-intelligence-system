"""Negative regression: MERGE-based child INSERTs are NOT idempotent across
two `book_atomic` calls that share the same parent `txn_id`.

The docstring at app/agents/booking.py:110-126 claims:

    # 4. child inserts (MERGE used for parameterized atomic INSERT — re-running
    # an identical txn_id is a no-op, but we never re-run because txn_id is a
    # fresh UUID4 per call).

The "no-op" claim is load-bearing for any retry/replay strategy — but the code
violates it: each child MERGE materialises its primary key as a freshly
generated `str(uuid4())` (line 126), independent of `txn_id`. So a Delta
warehouse evaluating the MERGE source row would ALWAYS see a NEW pk, and even
with `WHEN NOT MATCHED` semantics the dedup is keyed on `transaction_id`, so a
real warehouse would no-op on the second call — but the SQL we *send* still
embeds a different PK value, which means:
  - if the dedup key ever drifts (e.g. someone swaps to `ON t.{pk_col} = ...`)
    we silently get duplicate rows;
  - any audit log capturing executed params shows a non-deterministic stream;
  - the comment lies — `book_atomic` is not safe to retry with a forced
    txn_id from the caller layer.

This test mocks `warehouse_query` to record every SQL+params tuple, forces both
calls to produce the SAME parent txn_id (by stubbing `uuid4` deterministically),
and asserts ONE of the two real idempotency contracts:

  (A) the second call issues ZERO new MERGE INSERTs (true MERGE-WHEN-MATCHED
      idempotency — the function short-circuits on observed duplicate), OR
  (B) the second call's MERGE params reuse the SAME child PK as the first call
      (so warehouse-level dedup at PK granularity converges).

The current implementation satisfies NEITHER, so this test is RED.
"""
from __future__ import annotations

import re

import pytest

import app.agents.booking as booking_module


@pytest.fixture(autouse=True)
def _allow_dev_salt(monkeypatch):
    # bug #4: hash_patient_id refuses to run without explicit salt or DEV opt-in
    monkeypatch.setenv("AAROGYANET_DEV", "1")
    monkeypatch.delenv("PII_SALT", raising=False)


def _make_warehouse_recorder():
    """Returns (fake_warehouse_query, captured_calls).

    captured_calls: list[(query: str, params: list)] in execution order.
    The fake answers facility-exists + no-active-txn so book_atomic walks the
    full happy path through all 4 child MERGEs and the parent COMMIT update.
    """
    captured: list[tuple[str, list]] = []

    def fake(query, params=None, _retries=1):
        captured.append((query, list(params or [])))
        if "FROM workspace.default.gold_trust_final" in query:
            return [("5603",)]
        if (
            "FROM workspace.default.txn_atomic" in query
            and query.lstrip().startswith("SELECT")
        ):
            # Both calls observe "no active txn" — the duplicate-active-txn
            # guard would otherwise short-circuit the second call into REJECTED
            # for a totally unrelated reason (bug #6), and we want to see what
            # MERGE params actually get emitted on the second pass.
            return []
        return None

    return fake, captured


def _force_deterministic_uuid_sequence(monkeypatch):
    """Replace `app.agents.booking.uuid4` with a counter that returns the
    SAME txn_id for both calls, but DIFFERENT child PKs as the real code does.

    Sequence per call (5 uuid4 invocations):
      1. parent txn_id  -> "txn-PARENT" (identical across both calls)
      2-5. child PK for bed/ambulance/doctor/drug

    Across two calls that's 10 uuid4 calls. We freeze the parent slot to a
    constant "txn-PARENT" and let the child slots tick forward so we can
    observe whether the two calls reuse PKs or not.
    """
    state = {"i": 0}

    def fake_uuid4():
        # Per-call slot: 0 = parent txn, 1..4 = child PKs
        slot = state["i"] % 5
        state["i"] += 1
        if slot == 0:
            return "txn-PARENT"
        # Child PK: tag with a global ordinal so the test can see drift
        return f"child-pk-{state['i']}"

    monkeypatch.setattr(booking_module, "uuid4", fake_uuid4)


def test_neg_book_atomic_with_same_txn_id_is_not_idempotent(monkeypatch):
    """Two calls with identical (facility, patient) — and forced to share the
    same parent txn_id — must be idempotent at the MERGE layer.

    Currently they aren't: each child MERGE embeds a fresh `str(uuid4())` PK,
    so the SQL stream from call #2 is NOT a no-op of call #1. This test FAILS
    until either:
      - book_atomic detects the duplicate txn and skips child MERGEs entirely, or
      - the child PK is derived deterministically from (txn_id, table) so the
        warehouse can dedup at PK granularity.
    """
    fake, captured = _make_warehouse_recorder()
    monkeypatch.setattr(booking_module, "warehouse_query", fake)
    _force_deterministic_uuid_sequence(monkeypatch)

    # Call #1
    booking_module.book_atomic("5603", "patient_idempotent_xyz", {})
    first_call_records = list(captured)
    captured.clear()

    # Call #2 — identical inputs, identical forced txn_id
    booking_module.book_atomic("5603", "patient_idempotent_xyz", {})
    second_call_records = list(captured)

    # Sanity: parent txn_id was actually shared across both calls, otherwise
    # the test is checking the wrong invariant.
    parent_inserts = [
        (q, p) for q, p in first_call_records + second_call_records
        if q.lstrip().startswith("INSERT INTO workspace.default.txn_atomic")
    ]
    assert len(parent_inserts) == 2, (
        f"expected 2 parent INSERTs (one per call), got {len(parent_inserts)}: "
        f"{parent_inserts}"
    )
    txn_ids = {p[0] for _, p in parent_inserts}
    assert txn_ids == {"txn-PARENT"}, (
        f"test setup broken: parent txn_ids should be forced equal, got {txn_ids}"
    )

    # --- The actual idempotency assertion ---------------------------------
    # Extract child MERGE statements + their PK params from each call.
    # Param order at booking.py:126 is [txn_id, facility_id, init_status,
    # hashed_pid, child_pk], so child_pk is params[-1].
    def child_merges(records):
        merges = []
        for q, p in records:
            if "MERGE INTO" in q and "WHEN NOT MATCHED THEN INSERT" in q:
                # Pull the table name out of "MERGE INTO workspace.default.<tbl> t"
                m = re.search(r"MERGE INTO workspace\.default\.(\w+)\s+t", q)
                table = m.group(1) if m else "<unknown>"
                merges.append((table, p))
        return merges

    first_merges = child_merges(first_call_records)
    second_merges = child_merges(second_call_records)

    # The first call should have hit all 4 child tables — sanity guard before
    # we start comparing across calls.
    assert len(first_merges) == 4, (
        f"call #1 expected 4 child MERGEs, got {len(first_merges)}: {first_merges}"
    )

    # Two valid idempotency contracts; the implementation must satisfy ONE.
    # Contract A: second call issues ZERO child MERGEs (function short-circuits
    # on "txn already known" before re-emitting them).
    contract_a_holds = len(second_merges) == 0

    # Contract B: second call issues child MERGEs but reuses the SAME PK per
    # table as the first call, so warehouse-level dedup converges at PK.
    contract_b_holds = False
    if len(second_merges) == len(first_merges):
        first_pks_by_table = {tbl: params[-1] for tbl, params in first_merges}
        second_pks_by_table = {tbl: params[-1] for tbl, params in second_merges}
        contract_b_holds = first_pks_by_table == second_pks_by_table

    assert contract_a_holds or contract_b_holds, (
        "MERGE child-INSERT idempotency claim (booking.py:110-126) is violated.\n"
        f"call #1 child MERGEs: {first_merges}\n"
        f"call #2 child MERGEs: {second_merges}\n"
        "Neither contract holds:\n"
        "  (A) call #2 should issue ZERO child MERGEs (true short-circuit), OR\n"
        "  (B) call #2 should reuse the same child PK per table as call #1.\n"
        "Currently each child PK is a fresh uuid4() per call, so a real Delta "
        "warehouse only dedups by `transaction_id` — and any drift in the MERGE "
        "ON-clause silently introduces duplicate rows."
    )
