"""Negative tests for the 10 critical / high bugs from sweep #2 (2026-04-26).

Every test names the *boundary* being violated so reviewers can grep for the
boundary type rather than the bug number. Tests are RED while the bug is open
and GREEN once the implementation honors the contract.

Boundary taxonomy:
    transaction  → distributed lock + atomic CAS
    backpressure → bounded queue + deadline-based put
    io_deadline  → wall-clock SLA on every external call
    tenant       → ownership check before resource access
    secret       → defense-in-depth scrubber
    exception    → exhaustive taxonomy at I/O surface
    contract     → None vs zero / NaN preserved through numeric pipelines
"""
from __future__ import annotations

import ast
import asyncio
import re
import threading
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parent.parent


def _src(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def _function_node(rel: str, name: str) -> ast.FunctionDef | ast.AsyncFunctionDef:
    tree = ast.parse(_src(rel), filename=rel)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return node
    raise AssertionError(f"could not find function {name} in {rel}")


# ---------------------------------------------------------------------------
# Bug 1 — booking.py:33 — transaction boundary: threading.Lock is in-process
# only, so two replicas behind the same Railway service can both win the lock
# and double-commit. Documented in the file as bug #6 but not actually fixed
# at the boundary (still threading.Lock).
# ---------------------------------------------------------------------------

def test_critical_1_patient_lock_must_use_distributed_primitive() -> None:
    """booking._patient_lock must NOT rely solely on threading.Lock — a single
    Redis SETNX, Postgres advisory lock, or Delta unique constraint must be
    referenced as the cross-replica gate."""
    src = _src("app/agents/booking.py")
    fn = _function_node("app/agents/booking.py", "_patient_lock")
    fn_src = ast.get_source_segment(src, fn) or ""

    has_distributed_primitive = (
        "redis" in fn_src.lower()
        or "advisory_lock" in fn_src
        or "pg_advisory" in fn_src.lower()
        or re.search(r"unique\s+constraint", fn_src, re.I) is not None
        or "DistributedLock" in fn_src
    )
    assert has_distributed_primitive, (
        "critical #1 (transaction boundary): _patient_lock uses threading.Lock "
        "with no distributed primitive. Two replicas on Railway will both win "
        "the lock and double-commit a saga. Either gate at the warehouse with a "
        "unique constraint on (patient_id, status='RESERVED'), or wire a real "
        "distributed lock (Redis SETNX / Postgres advisory)."
    )


# ---------------------------------------------------------------------------
# Bug 2 — booking.py:137 — transaction boundary: the dup-active-txn SELECT
# happens BEFORE the parent INSERT, so two concurrent sagas for the same
# patient both pass the SELECT, both INSERT a parent, and we double-book.
# ---------------------------------------------------------------------------

def test_critical_2_dup_txn_check_must_be_atomic_with_parent_insert() -> None:
    """The dup-active-txn check + parent INSERT must run as a single MERGE / CAS,
    not check-then-insert."""
    src = _src("app/agents/booking.py")
    fn = _function_node("app/agents/booking.py", "_book_atomic_inner")
    fn_src = ast.get_source_segment(src, fn) or ""

    # Find the SELECT for active txns and the parent INSERT.
    sel = re.search(
        r"SELECT\s+transaction_id\s+FROM\s+workspace\.default\.txn_atomic.*?status\s+IN",
        fn_src, re.I | re.S,
    )
    ins = re.search(r"INSERT\s+INTO\s+workspace\.default\.txn_atomic", fn_src, re.I)
    assert sel and ins, "precondition: both dup-check SELECT and parent INSERT not found"

    # The parent insert must be a MERGE (CAS) OR the SELECT must be a SELECT FOR
    # UPDATE / INSERT ... WHERE NOT EXISTS — anything that closes the gap.
    has_atomic_pattern = bool(
        re.search(r"MERGE\s+INTO\s+workspace\.default\.txn_atomic", fn_src, re.I)
        or re.search(r"INSERT\s+INTO\s+workspace\.default\.txn_atomic.*WHERE\s+NOT\s+EXISTS", fn_src, re.I | re.S)
        or re.search(r"FOR\s+UPDATE", fn_src, re.I)
    )
    assert has_atomic_pattern, (
        "critical #2 (transaction boundary): dup-active-txn check is a separate "
        "SELECT followed by a separate INSERT. Two concurrent calls both pass "
        "the SELECT and both INSERT a parent. Replace with MERGE INTO txn_atomic "
        "USING (SELECT ... WHERE NOT EXISTS in active set) so the gate is atomic."
    )


# ---------------------------------------------------------------------------
# Bug 3 — booking.py:248 — transaction boundary: rollback failure leaves
# children CANCELLED but parent stuck at RESERVED, no audit ledger row, no
# alert. Final status is reported as ROLLBACK_FAILED but the warehouse drift
# is invisible to ops dashboards.
# ---------------------------------------------------------------------------

def test_critical_3_rollback_failure_must_record_drift_alert() -> None:
    """A rollback that itself fails must write a drift-marker row (or at
    minimum logger.error with an alertable tag) so ops can reconcile."""
    src = _src("app/agents/booking.py")
    fn = _function_node("app/agents/booking.py", "_book_atomic_inner")
    fn_src = ast.get_source_segment(src, fn) or ""

    # Look for an alertable signal on the rollback-failed branch:
    # logger.error / logger.critical with a stable tag, OR an explicit drift
    # ledger insert.
    has_alert = (
        re.search(r"logger\.(error|critical)\([^)]*rollback", fn_src, re.I) is not None
        or "rollback_drift" in fn_src.lower()
        or re.search(r"INSERT\s+INTO\s+workspace\.default\.\w*drift", fn_src, re.I) is not None
    )
    assert has_alert, (
        "critical #3 (transaction boundary): rollback failure path returns "
        "ROLLBACK_FAILED status but emits no logger.error with a drift tag and "
        "writes no audit row. Ops cannot detect the warehouse drift between "
        "parent.status='RESERVED' and children.status='CANCELLED'."
    )


# ---------------------------------------------------------------------------
# Bug 4 — main.py:349 — backpressure boundary: SSE producer calls
# `await queue.put(...)` directly. The queue now has maxsize=64 (good) but a
# slow consumer fills the queue and the producer awaits forever, holding the
# trace_id task and the heartbeat task hostage.
# ---------------------------------------------------------------------------

def test_critical_4_sse_producer_must_use_bounded_put_with_deadline() -> None:
    """The SSE producer/heartbeat must put with a deadline (asyncio.wait_for or
    boundaries.bounded_put) so a slow consumer cannot hang the producer."""
    src = _src("app/main.py")
    fn = _function_node("app/main.py", "sse")
    fn_src = ast.get_source_segment(src, fn) or ""

    has_deadline_put = (
        re.search(r"asyncio\.wait_for\s*\([^)]*queue\.put", fn_src) is not None
        or "bounded_put" in fn_src
    )
    assert has_deadline_put, (
        "critical #4 (backpressure boundary): producer/heartbeat call "
        "`await queue.put(...)` with no deadline. With maxsize=64 (good) and a "
        "slow consumer the producer blocks indefinitely. Use "
        "boundaries.bounded_put(queue, item, deadline_s=5.0) — drop heartbeats, "
        "abort producer on payload overflow."
    )


# ---------------------------------------------------------------------------
# Bug 5 — router.py:462 — contract boundary: 0.0 trust treated as falsy.
# This was patched in the prior batch; lock the fix.
# ---------------------------------------------------------------------------

def test_critical_5_router_preserves_zero_trust_calibrated() -> None:
    """A row with trust_calibrated == 0.0 (real zero) must NOT silently fall
    back to trust_score; the float check must be `is not None`."""
    src = _src("app/agents/router.py")
    # Find the ranking loop. We accept either the explicit None-check pattern
    # or the new pattern that uses `is not None` instead of `or`.
    has_or_trap = bool(
        re.search(
            r"float\s*\(\s*row\.get\(['\"]trust_effective['\"]\)\s+or\s+"
            r"row\.get\(['\"]trust_score['\"]\)\s+or\s+0\.0\s*\)",
            src,
        )
    )
    assert not has_or_trap, (
        "critical #5 (contract boundary): the `or` chain treats 0.0 as missing. "
        "Use explicit `is not None` checks so a calibrated-down-to-zero hospital "
        "is correctly recognized as low-trust, not silently rescored."
    )


# ---------------------------------------------------------------------------
# Bug 6 — router.py:465 — contract boundary: NULL p_bed → 0.0 → composite
# score zeroed → hospital silently dropped from rankings.
# ---------------------------------------------------------------------------

def test_critical_6_null_p_bed_must_not_silently_drop_hospital() -> None:
    """Hospitals with NULL p_bed must keep a non-zero default so they are
    ranked, not silently dropped."""
    src = _src("app/agents/router.py")
    # The fix landed as: `p_bed = preds.get(fid); if p_bed is None: p_bed =
    # gold_p_bed if gold_p_bed is not None else 0.5`. Lock that pattern.
    assert re.search(r"if\s+gold_p_bed\s+is\s+not\s+None\s+else\s+0\.5", src), (
        "critical #6 (contract boundary): the 0.5 default for missing p_bed is "
        "not present in router.py. Without it, NULL p_bed → 0.0 zeros the "
        "composite score and drops the hospital from /recommend output."
    )


# ---------------------------------------------------------------------------
# Bug 7 — main.py:549, 685 — io_deadline boundary: warehouse_query is wrapped
# in `asyncio.to_thread` but no `asyncio.wait_for` deadline. db.py has
# socket_timeout=45 + 1 retry → up to ~92s per call, and routes chain 5+
# calls. A Databricks outage hangs the FastAPI worker for >7 minutes.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("route_fn", ["outcome_route", "ngo_data_endpoint"])
def test_critical_7_warehouse_calls_must_have_io_deadline(route_fn: str) -> None:
    """Every `to_thread(warehouse_query, ...)` in mutating / cached routes must
    be wrapped in an io_deadline (asyncio.wait_for or boundaries.with_io_deadline)."""
    src = _src("app/main.py")
    fn = _function_node("app/main.py", route_fn)
    fn_src = ast.get_source_segment(src, fn) or ""

    if "warehouse_query" not in fn_src:
        pytest.skip(f"{route_fn} has no warehouse_query call")

    has_deadline_wrapper = (
        "with_io_deadline" in fn_src
        or re.search(r"asyncio\.wait_for\s*\([^)]*to_thread", fn_src) is not None
    )
    assert has_deadline_wrapper, (
        f"critical #7 (io_deadline boundary): {route_fn} calls warehouse_query "
        "via to_thread without an asyncio.wait_for / with_io_deadline wrapper. "
        "A Databricks outage hangs the worker for socket_timeout * (1+retries) "
        "= ~92s per call × N chained calls. Add a route-level SLA."
    )


# ---------------------------------------------------------------------------
# Bug 8 — genie.py:136 — tenant boundary: ask() accepts ANY conversation_id
# and forwards it to Databricks Genie. There is no "this conversation belongs
# to the calling demo session" check, so a sponsor route consumer can read
# any other consumer's conversation.
# ---------------------------------------------------------------------------

def test_critical_8_genie_ask_must_check_conversation_ownership() -> None:
    """GenieClient.ask must verify the conversation_id is owned by the caller —
    via a session/principal arg or boundaries.as_owner."""
    src = _src("app/sponsor/genie.py")
    fn = _function_node("app/sponsor/genie.py", "ask")
    fn_src = ast.get_source_segment(src, fn) or ""

    has_ownership_check = (
        "as_owner" in fn_src
        or re.search(r"\bowner\b|\bprincipal\b|\bsession_id\b", fn_src, re.I) is not None
    )
    assert has_ownership_check, (
        "critical #8 (tenant boundary): GenieClient.ask forwards the supplied "
        "conversation_id to Databricks with no ownership check. Any sponsor "
        "consumer can read another consumer's chat history. Pass an owner / "
        "session_id arg through and call boundaries.as_owner before forwarding."
    )


# ---------------------------------------------------------------------------
# Bug 9 — scrub.py — secret boundary: my prior batch tightened the regex to
# require a Fish-key context prefix, which fixed the txn-id false positive
# but introduced a worse bug — a raw 32-hex key WITHOUT the prefix now leaks.
# Defense-in-depth: scrub bare 32-hex unless surrounded by a known-safe
# transaction context.
# ---------------------------------------------------------------------------

def test_critical_9a_raw_fish_key_without_prefix_must_be_redacted() -> None:
    """A bare 32-hex string in a log line (no transaction-id context) must be
    scrubbed — that's the original Fish-key shape we wanted to redact."""
    from app.sponsor.scrub import apply_sponsor_patterns

    raw_key = "11fc20c6521f4a869dc4b7cce9a5f0ea"
    log_line = f"voice sidecar dump: {raw_key} bytes_sent=1234"
    redacted = apply_sponsor_patterns(log_line)

    assert raw_key not in redacted, (
        "critical #9 (secret boundary): a raw 32-hex string with no transaction "
        "context leaks through the scrubber. Defense-in-depth requires bare "
        "hex32 to be redacted unless explicitly preceded by transaction_id= / "
        "txn= / trace_id= / sha256= or a UUID-with-hyphens shape."
    )


def test_critical_9b_transaction_id_must_survive_scrubber() -> None:
    """A 32-hex transaction id in `transaction_id=<hex>` shape must NOT be
    redacted — it is an audit identifier, not a secret."""
    from app.sponsor.scrub import apply_sponsor_patterns

    txn = "a3f1e2b4c5d6e7f8a1b2c3d4e5f60011"
    log_line = f"booking committed transaction_id={txn} facility=5603"
    redacted = apply_sponsor_patterns(log_line)

    assert txn in redacted, (
        "critical #9 (secret boundary): a legitimate transaction_id was "
        "scrubbed. The safe-context allowlist must include transaction_id= / "
        "txn= / trace_id= / sha256= so audit lines stay readable."
    )


# ---------------------------------------------------------------------------
# Bug 10 — reasoning_stream.py:68 — exception boundary: the prior batch added
# httpx.TimeoutException / ReadError / RemoteProtocolError. NetworkError and
# ProtocolError are still uncovered, so a TLS hand-shake failure or HTTP/2
# protocol violation escapes.
# ---------------------------------------------------------------------------

def test_critical_10_reasoning_stream_must_cover_full_httpx_taxonomy() -> None:
    """stream_endpoint's except clause must cover the network + protocol
    branches of the httpx exception hierarchy, not only Timeout/Read/Remote."""
    src = _src("app/agents/reasoning_stream.py")
    fn = _function_node("app/agents/reasoning_stream.py", "stream_endpoint")
    fn_src = ast.get_source_segment(src, fn) or ""

    # The simplest correct fix is to catch httpx.HTTPError (the common parent
    # of TimeoutException, NetworkError, ProtocolError, and RemoteProtocolError).
    # We accept either that single parent OR the explicit list including all
    # missing branches.
    has_parent = "httpx.HTTPError" in fn_src
    has_full_list = all(
        cls in fn_src for cls in ("TimeoutException", "NetworkError", "ProtocolError")
    )
    assert has_parent or has_full_list, (
        "critical #10 (exception boundary): stream_endpoint catches "
        "TimeoutException / ReadError / RemoteProtocolError but leaves "
        "NetworkError (TLS / DNS / SYN) and ProtocolError (HTTP/2 violation) "
        "uncovered. Either catch httpx.HTTPError (parent) or list all four."
    )


# ---------------------------------------------------------------------------
# Boundary self-test — the boundaries module itself must keep its contract.
# ---------------------------------------------------------------------------

def test_boundary_with_io_deadline_raises_violation_on_timeout() -> None:
    """boundaries.with_io_deadline must convert asyncio.TimeoutError into
    BoundaryViolation so callers can pattern-match on a single exception."""
    from app.boundaries import BoundaryViolation, with_io_deadline

    async def slow():
        await asyncio.sleep(5.0)

    with pytest.raises(BoundaryViolation):
        asyncio.run(with_io_deadline(slow(), deadline_s=0.05, op="self_test"))


def test_boundary_bounded_put_returns_false_on_full_queue() -> None:
    """boundaries.bounded_put must return False (not block) when the queue is
    full past the deadline."""
    from app.boundaries import bounded_put

    async def scenario() -> bool:
        q: asyncio.Queue = asyncio.Queue(maxsize=1)
        await q.put("first")  # fills the queue
        return await bounded_put(q, "second", deadline_s=0.05, op="self_test")

    result = asyncio.run(scenario())
    assert result is False, (
        "boundaries.bounded_put must return False when a full queue stays full "
        "past the deadline; returning True or hanging breaks the back-pressure "
        "contract for SSE producers."
    )


def test_boundary_as_owner_blocks_anonymous_access() -> None:
    """boundaries.as_owner must reject calls where either side is None."""
    from app.boundaries import BoundaryViolation, as_owner

    with pytest.raises(BoundaryViolation):
        as_owner(expected_owner=None, resource_owner="alice", resource_kind="conv")
    with pytest.raises(BoundaryViolation):
        as_owner(expected_owner="alice", resource_owner=None, resource_kind="conv")
    with pytest.raises(BoundaryViolation):
        as_owner(expected_owner="alice", resource_owner="bob", resource_kind="conv")
    # Legitimate match must NOT raise.
    as_owner(expected_owner="alice", resource_owner="alice", resource_kind="conv")
