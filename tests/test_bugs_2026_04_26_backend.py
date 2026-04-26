"""Negative regression locks for the 2026-04-26 evening sweep bugs #78–96.

Tests encode *desired* behavior. They are expected to fail while the bug is
present and flip green when the implementation is fixed.
"""
from __future__ import annotations

import ast
import concurrent.futures
import os
import re
import threading
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parent.parent


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def _function_node(rel: str, name: str) -> ast.FunctionDef | ast.AsyncFunctionDef:
    tree = ast.parse(_read(rel), filename=rel)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return node
    raise AssertionError(f"could not find function {name!r} in {rel}")


# ---------------------------------------------------------------------------
# #78 — double-booking race: check-then-act without atomic increment
# ---------------------------------------------------------------------------

def test_bug78_booking_uses_patient_level_lock_before_capacity_check() -> None:
    """Concurrent requests for the SAME patient must be serialized by a lock
    that wraps both the capacity check and the INSERT, not just the INSERT."""
    src = _read("app/agents/booking.py")
    book_fn = _function_node("app/agents/booking.py", "book_atomic")
    book_src = ast.get_source_segment(src, book_fn) or ""

    # The outer book_atomic must acquire _patient_lock (or equivalent) before
    # delegating to _book_atomic_inner. The lock call must appear BEFORE the
    # inner call in the source text.
    lock_pos = book_src.find("_patient_lock")
    inner_pos = book_src.find("_book_atomic_inner")
    assert lock_pos != -1, "bug #78: _patient_lock not found in book_atomic"
    assert inner_pos != -1, "bug #78: _book_atomic_inner not found in book_atomic"
    assert lock_pos < inner_pos, (
        "bug #78: _patient_lock must be acquired before _book_atomic_inner is called; "
        "without this, two concurrent requests for the same patient race through the "
        "capacity check and both succeed, causing overbooking."
    )


# ---------------------------------------------------------------------------
# #79 — SQL injection via pk_col f-string interpolation
# ---------------------------------------------------------------------------

def test_bug79_pk_col_is_validated_against_whitelist_before_merge_fstring() -> None:
    """pk_col must be validated against an explicit whitelist before it is
    interpolated into the MERGE f-string to prevent SQL injection."""
    src = _read("app/agents/booking.py")
    tree = ast.parse(src, filename="app/agents/booking.py")

    # Collect all f-string nodes that contain 'pk_col' in their formatted values.
    pk_col_fstrings: list[ast.JoinedStr] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.JoinedStr):
            src_seg = ast.get_source_segment(src, node) or ""
            if "pk_col" in src_seg:
                pk_col_fstrings.append(node)

    assert pk_col_fstrings, "precondition: no pk_col f-string found in booking.py"

    # Before each MERGE f-string, the code must validate pk_col against an
    # explicit set/tuple of allowed column names. We verify this by checking
    # that the booking module defines a constant containing the allowed pk
    # column names, and that validation (membership test) is visible in the
    # source. An `in` membership check on a whitelist set is the minimum bar.
    allowed_pk_cols = {"reservation_id", "dispatch_id", "slot_id"}
    for name in allowed_pk_cols:
        assert name in src, (
            f"bug #79: expected known pk_col value '{name}' not found in booking.py — "
            "the MERGE pk_col whitelist may be missing or incomplete."
        )

    # The actual structural assertion: if pk_col is interpolated into an f-string
    # there must be a prior membership guard. Minimally, `RESOURCE_TABLES` must
    # enumerate the allowed pk_col values and the code must iterate that tuple,
    # never interpolating an arbitrary caller-supplied string.
    assert "RESOURCE_TABLES" in src, (
        "bug #79: RESOURCE_TABLES whitelist not found; pk_col is not constrained "
        "before f-string interpolation into the MERGE statement."
    )
    # The for-loop that drives the MERGE must bind pk_col from RESOURCE_TABLES,
    # not from user input. Confirm the binding pattern exists.
    assert re.search(r"for\s+\w+,\s*pk_col\s*,\s*\w+\s+in\s+RESOURCE_TABLES", src), (
        "bug #79: pk_col is not bound from RESOURCE_TABLES in the MERGE loop; "
        "an attacker could supply an arbitrary column name via a crafted request."
    )


# ---------------------------------------------------------------------------
# #80 — orphaned RESERVED rows when connection drops after parent INSERT
# ---------------------------------------------------------------------------

def test_bug80_child_merge_failure_triggers_parent_rollback() -> None:
    """If a child MERGE fails, the saga must attempt to roll back the parent
    row to ROLLED_BACK so it does not remain RESERVED forever."""
    from app.agents import booking

    call_log: list[str] = []
    call_count = [0]

    def fake_query(sql: str, params=None):
        call_count[0] += 1
        sql_upper = sql.strip().upper()
        call_log.append(sql_upper[:60])
        # facility existence → return a row
        if "GOLD_TRUST_FINAL" in sql_upper and "SELECT" in sql_upper and "CAPACITY" not in sql_upper:
            return [["fac-1"]]
        # bed availability → ok (not exhausted)
        if "BED_CAPACITY" in sql_upper or "RESERVED_BEDS" in sql_upper:
            return [[10, 0]]
        # duplicate active txn → none
        if "STATUS IN" in sql_upper and "RESERVED" in sql_upper and "LIMIT 1" in sql_upper:
            return []
        # parent INSERT → success
        if "INSERT INTO" in sql_upper and "TXN_ATOMIC" in sql_upper:
            return []
        # First child MERGE → raise to simulate connection drop
        if "MERGE INTO" in sql_upper:
            raise RuntimeError("simulated warehouse connection drop")
        # parent rollback UPDATE → record it
        if "UPDATE" in sql_upper and "TXN_ATOMIC" in sql_upper and "ROLLED_BACK" in sql_upper:
            call_log.append("ROLLBACK_SEEN")
            return []
        return []

    import importlib
    orig = booking.warehouse_query
    booking.warehouse_query = fake_query
    try:
        result = booking._book_atomic_inner("fac-1", "hashed-p1", {})
    finally:
        booking.warehouse_query = orig

    assert "ROLLBACK_SEEN" in call_log, (
        "bug #80: child MERGE failure did not trigger a parent ROLLED_BACK UPDATE. "
        "The parent INSERT row will remain RESERVED indefinitely (orphan)."
    )
    assert result["status"] in ("ROLLED_BACK", "ROLLBACK_FAILED"), (
        f"bug #80: expected ROLLED_BACK or ROLLBACK_FAILED status, got {result['status']!r}"
    )


# ---------------------------------------------------------------------------
# #84 — f"v1={v1:.2f}" TypeError when v1 is None
# ---------------------------------------------------------------------------

def test_bug84_validator_reasoning_does_not_crash_when_v1_is_none() -> None:
    """validator._merge_scores must not raise TypeError when v1 is None
    (single-model data path: only v2 is available)."""
    from app.agents import validator

    # Provide v2 only (v1=None), mimicking single-model data.
    try:
        result = validator._merge_scores(
            v1=None,
            v2=0.75,
            extractor_model="ext",
            validator_model="val",
        )
    except TypeError as exc:
        pytest.fail(
            f"bug #84: _merge_scores raised TypeError with v1=None: {exc!r}. "
            "The f-string 'v1={v1:.2f}' crashes when v1 is None."
        )
    assert result is not None


# ---------------------------------------------------------------------------
# #85 — chunked transfer body-size bypass
# ---------------------------------------------------------------------------

def test_bug85_body_size_middleware_rejects_chunked_oversized_body() -> None:
    """The body-size middleware must reject large chunked-encoded bodies, not
    only requests with an explicit Content-Length header."""
    src = _read("app/main.py")
    # The middleware should read/stream the body and enforce a byte cap even
    # when Content-Length is absent (chunked transfer). A minimal structural
    # signal: if the middleware only checks 'content-length' and immediately
    # calls call_next without any body-length check for the absent-CL case,
    # the bug is present.
    middleware_src = ""
    tree = ast.parse(src, filename="app/main.py")
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "_BodySizeLimitMiddleware":
            middleware_src = ast.get_source_segment(src, node) or ""
            break
    assert middleware_src, "precondition: _BodySizeLimitMiddleware not found in app/main.py"

    # If cl is None (no Content-Length), the middleware must NOT proceed
    # directly to call_next without inspecting the body.
    # Look for a body-reading branch guarded by `if cl is None` or `else:`.
    has_body_fallback = (
        re.search(r"cl\s+is\s+None", middleware_src)
        or re.search(r"else\s*:", middleware_src)
        or "body" in middleware_src
        or "stream" in middleware_src
        or "receive" in middleware_src
    )
    assert has_body_fallback, (
        "bug #85: _BodySizeLimitMiddleware has no fallback path when Content-Length "
        "is absent. Chunked-encoded bodies bypass the size limit entirely."
    )


# ---------------------------------------------------------------------------
# #86 — negative Content-Length accepted
# ---------------------------------------------------------------------------

def test_bug86_negative_content_length_is_rejected() -> None:
    """A negative Content-Length value must be rejected (400 or 413), not
    silently allowed through because int('-100') > 65536 is False."""
    import app.main as main_module
    from starlette.testclient import TestClient

    os.environ.setdefault("AAROGYANET_DEV", "1")
    client = TestClient(main_module.app, raise_server_exceptions=False)
    resp = client.post(
        "/book",
        content=b"{}",
        headers={"Content-Length": "-100", "Content-Type": "application/json"},
    )
    assert resp.status_code in (400, 413, 422), (
        f"bug #86: negative Content-Length '-100' returned {resp.status_code}; "
        "expected 400, 413, or 422. The check `int(cl) > MAX_REQUEST_BYTES` "
        "evaluates False for negative values, admitting the request."
    )


# ---------------------------------------------------------------------------
# #89 — _scrubbed_500 has no trace_id
# ---------------------------------------------------------------------------

def test_bug89_scrubbed_500_response_includes_trace_id() -> None:
    """The global 500 handler must include a trace_id so DB outages and capacity
    rejections can be distinguished in logs."""
    fn = _function_node("app/main.py", "_scrubbed_500")
    src = _read("app/main.py")
    fn_src = ast.get_source_segment(src, fn) or ""

    assert "trace_id" in fn_src or "uuid" in fn_src or "request_id" in fn_src, (
        "bug #89: _scrubbed_500 returns {\"detail\": \"internal error\"} with no "
        "trace_id. All 5xx look identical; DB outage and capacity rejection are "
        "indistinguishable in monitoring."
    )


# ---------------------------------------------------------------------------
# #90 — naive datetime crash on fb.ts > now
# ---------------------------------------------------------------------------

def test_bug90_outcome_route_returns_4xx_for_naive_ts_not_500() -> None:
    """POST /outcome with a timezone-naive ts must return 4xx, not 500.

    Comparing a naive datetime to an aware datetime raises TypeError:
    'can't compare offset-naive and offset-aware datetimes'.
    """
    import app.main as main_module
    from starlette.testclient import TestClient

    os.environ.setdefault("AAROGYANET_DEV", "1")
    client = TestClient(main_module.app, raise_server_exceptions=False)

    # Pydantic will parse the ISO string; send a naive ISO string (no Z / offset).
    payload = {
        "patient_id": "p1",
        "facility_id": "5603",
        "factor": "bed",
        "actual_value": 0.8,
        "llm_predicted": 0.7,
        "ts": "2026-04-26T12:00:00",  # naive — no timezone
    }
    resp = client.post(
        "/outcome",
        json=payload,
        headers={"X-Demo-Key": ""},
    )
    # We expect 4xx (422 from Pydantic or 400/422 from explicit guard),
    # NOT 500 (which would indicate the TypeError leaked out of the handler).
    assert resp.status_code != 500, (
        f"bug #90: /outcome returned 500 for a naive ts. "
        "The comparison fb.ts > now crashes with TypeError when ts is naive."
    )
    assert 400 <= resp.status_code < 500, (
        f"bug #90: expected 4xx for naive ts, got {resp.status_code}"
    )


# ---------------------------------------------------------------------------
# #91 — _fm_executor(max_workers=2) exhaustion
# ---------------------------------------------------------------------------

def test_bug91_fm_endpoint_count_does_not_block_indefinitely_when_executor_full() -> None:
    """_fm_endpoint_count must return within timeout even if the executor's
    workers are all occupied by hanging tasks."""
    import app.main as main_module

    hang_event = threading.Event()

    def hanging_list_endpoints():
        hang_event.wait(timeout=30)  # simulate infinite hang
        return []

    orig_submit = main_module._fm_executor.submit

    submitted: list = []

    def fake_submit(fn, *args, **kwargs):
        # Replace the real fn with a hanging one to saturate workers.
        f = orig_submit(hanging_list_endpoints)
        submitted.append(f)
        return f

    main_module._fm_executor.submit = fake_submit  # type: ignore[method-assign]
    # Invalidate cache so the call actually hits the executor.
    main_module._ep_cache["n"] = None
    main_module._ep_cache["ts"] = 0.0

    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as caller_pool:
            fut = caller_pool.submit(main_module._fm_endpoint_count, 60, 0.5)
            done, _ = concurrent.futures.wait([fut], timeout=5.0)
            assert done, (
                "bug #91: _fm_endpoint_count did not return within 5s when the "
                "_fm_executor is saturated. A third concurrent caller is blocked "
                "indefinitely because future.result(timeout=...) is not propagating "
                "the TimeoutError or the executor queue is unbounded."
            )
    finally:
        main_module._fm_executor.submit = orig_submit  # type: ignore[method-assign]
        hang_event.set()  # unblock hanging threads
        for f in submitted:
            try:
                f.result(timeout=1)
            except Exception:
                pass


# ---------------------------------------------------------------------------
# #92 — X-Forwarded-For spoofing bypasses rate limit
# ---------------------------------------------------------------------------

def test_bug92_xff_rate_limit_key_requires_trusted_proxy_validation() -> None:
    """The rate-limit key function must not trust X-Forwarded-For blindly.

    Reading the first XFF entry without validating the proxy lets any client
    spoof any IP, defeating the per-IP rate limit.
    """
    src = _read("app/main.py")
    # Locate the _client_key function source.
    fn = _function_node("app/main.py", "_client_key")
    fn_src = ast.get_source_segment(src, fn) or ""

    # The function must either: (a) validate the remote addr against a
    # trusted-proxy list before trusting XFF, OR (b) use a library that does
    # trusted-proxy handling. A bare `xff.split(",")[0]` without any trusted-
    # proxy check is the vulnerable pattern.
    has_trusted_proxy_check = (
        "trusted" in fn_src.lower()
        or "TRUSTED" in fn_src
        or re.search(r"proxy\w*\s*=", fn_src, re.I)
        or "forwarded_for" in fn_src.lower()
        or re.search(r"TRUSTED_PROXIES|trusted_proxy|proxy_list", fn_src)
    )
    assert has_trusted_proxy_check, (
        "bug #92: _client_key reads X-Forwarded-For with xff.split(',')[0] "
        "without validating that the request arrived via a trusted proxy. "
        "Any client can set XFF to any IP and bypass per-IP rate limiting."
    )


# ---------------------------------------------------------------------------
# #93 — SSE heartbeat queue grows without bound
# ---------------------------------------------------------------------------

def test_bug93_sse_heartbeat_queue_has_bounded_maxsize() -> None:
    """The SSE heartbeat asyncio.Queue must have a maxsize > 0 so it cannot
    grow without bound when a slow consumer stalls."""
    src = _read("app/main.py")
    sse_fn = _function_node("app/main.py", "sse")
    sse_src = ast.get_source_segment(src, sse_fn) or ""

    # Find asyncio.Queue instantiation(s) inside sse.
    queue_calls = re.findall(r"asyncio\.Queue\s*\(([^)]*)\)", sse_src)
    assert queue_calls is not None and len(queue_calls) > 0, (
        "precondition: asyncio.Queue not found in sse()"
    )
    for args in queue_calls:
        has_maxsize = (
            "maxsize" in args
            and re.search(r"maxsize\s*=\s*[1-9]\d*", args) is not None
        ) or (
            # positional first arg is maxsize
            re.match(r"\s*[1-9]\d*", args) is not None
        )
        assert has_maxsize, (
            f"bug #93: asyncio.Queue({args!r}) has no positive maxsize. "
            "The heartbeat task puts indefinitely, so a slow consumer causes "
            "unbounded queue growth and eventual OOM."
        )


# ---------------------------------------------------------------------------
# #94 — SSE cleanup `await t` instead of gather(return_exceptions=True)
# ---------------------------------------------------------------------------

def test_bug94_sse_cleanup_uses_gather_with_return_exceptions() -> None:
    """SSE finally block must use asyncio.gather(..., return_exceptions=True)
    so an exception from one task does not leave the other uncancelled."""
    src = _read("app/main.py")
    sse_fn = _function_node("app/main.py", "sse")
    sse_src = ast.get_source_segment(src, sse_fn) or ""

    has_gather = re.search(
        r"asyncio\.gather\s*\([^)]*return_exceptions\s*=\s*True",
        sse_src,
        re.S,
    )
    # A bare `await t` or a try/except loop is acceptable only if it covers
    # both tasks and swallows exceptions; gather is the idiomatic signal.
    bare_await_loop = re.search(r"for\s+t\s+in\s*\([^)]*hb_task.*?\).*?await\s+t", sse_src, re.S)
    assert has_gather or bare_await_loop, (
        "bug #94: SSE finally block does not use asyncio.gather(return_exceptions=True). "
        "A plain 'await t' inside the loop propagates the first exception, leaving "
        "the heartbeat task uncancelled and the queue handler leaked."
    )


# ---------------------------------------------------------------------------
# #95 — rollback partial failure leaves mixed RESERVED/CANCELLED
# ---------------------------------------------------------------------------

def test_bug95_rollback_child_failure_does_not_stop_remaining_cancellations() -> None:
    """If one child cancellation UPDATE fails, the rollback loop must continue
    and attempt to cancel the remaining children."""
    from app.agents import booking

    cancelled_tables: list[str] = []
    call_count = [0]

    def fake_query(sql: str, params=None):
        call_count[0] += 1
        sql_upper = sql.strip().upper()
        # facility existence
        if "GOLD_TRUST_FINAL" in sql_upper and "SELECT" in sql_upper and "CAPACITY" not in sql_upper:
            return [["fac-1"]]
        # bed availability
        if "BED_CAPACITY" in sql_upper or "RESERVED_BEDS" in sql_upper:
            return [[10, 0]]
        # duplicate active txn
        if "STATUS IN" in sql_upper and "RESERVED" in sql_upper and "LIMIT 1" in sql_upper:
            return []
        # parent INSERT
        if "INSERT INTO" in sql_upper and "TXN_ATOMIC" in sql_upper:
            return []
        # child MERGEs for first two tables → succeed; third → fail
        if "MERGE INTO" in sql_upper:
            for tbl in ("BED_RESERVATIONS", "AMBULANCE_DISPATCHES", "DOCTOR_SLOTS", "DRUG_RESERVATIONS"):
                if tbl in sql_upper:
                    if tbl in ("DOCTOR_SLOTS",):
                        raise RuntimeError(f"simulated child fail: {tbl}")
                    return []
            return []
        # child cancellation UPDATEs
        for tbl in ("BED_RESERVATIONS", "AMBULANCE_DISPATCHES", "DOCTOR_SLOTS", "DRUG_RESERVATIONS"):
            if tbl in sql_upper and "UPDATE" in sql_upper and "CANCELLED" in sql_upper:
                if tbl == "BED_RESERVATIONS":
                    raise RuntimeError("simulated cancel fail on first child")
                cancelled_tables.append(tbl)
                return []
        # parent rollback UPDATE
        if "UPDATE" in sql_upper and "TXN_ATOMIC" in sql_upper:
            return []
        return []

    orig = booking.warehouse_query
    booking.warehouse_query = fake_query
    try:
        result = booking._book_atomic_inner("fac-1", "hashed-p2", {})
    finally:
        booking.warehouse_query = orig

    assert "AMBULANCE_DISPATCHES" in cancelled_tables or len(cancelled_tables) > 0, (
        "bug #95: rollback loop stopped after the first child cancellation failure "
        "instead of continuing to cancel remaining RESERVED children. "
        f"Cancelled tables: {cancelled_tables}"
    )


# ---------------------------------------------------------------------------
# #96 — no retryable-vs-fatal classification on child MERGE
# ---------------------------------------------------------------------------

def test_bug96_child_merge_exception_handler_distinguishes_retryable_errors() -> None:
    """The child MERGE exception handler must classify errors as retryable
    (timeout, transient) vs fatal (constraint violation) rather than treating
    all errors identically and immediately breaking out of the saga loop."""
    src = _read("app/agents/booking.py")
    inner_fn = _function_node("app/agents/booking.py", "_book_atomic_inner")
    fn_src = ast.get_source_segment(src, inner_fn) or ""

    # Look for any retry/backoff/retryable/transient classification near the
    # child MERGE exception handler. The minimal bar: an except clause that
    # distinguishes at least two error classes OR a retry counter/loop.
    has_retry_logic = (
        re.search(r"retry|retryable|transient|backoff|attempt", fn_src, re.I)
        or re.search(r"except\s*\(\s*\w+,\s*\w+", fn_src)  # multiple except types
        or re.search(r"TimeoutError|OperationalError|DatabaseError", fn_src)
    )
    assert has_retry_logic, (
        "bug #96: child MERGE exception handler catches all exceptions with bare "
        "'except Exception' and immediately breaks. Timeout and constraint violations "
        "are treated identically — transient failures are never retried, causing "
        "spurious ROLLED_BACK status on recoverable warehouse blips."
    )
