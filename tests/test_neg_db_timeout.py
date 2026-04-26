"""Negative test: prove app/db.py:run_query has no socket/HTTP timeout.

A stuck Databricks warehouse will block the worker thread indefinitely
because `sql.connect(...)` is called without `_socket_timeout` /
`http_timeout`, and the retry handler only catches narrow Databricks-
specific exceptions (not transient network errors like ConnectionError
or OSError).

This test uses pure AST inspection — no live Databricks, no monkey-
patching. It must FAIL on the current implementation.
"""
from __future__ import annotations

import ast
from pathlib import Path

DB_FILE = Path(__file__).resolve().parent.parent / "app" / "db.py"


def _load_module() -> ast.Module:
    with open(DB_FILE, "r", encoding="utf-8") as fh:
        source = fh.read()
    return ast.parse(source, filename=str(DB_FILE))


def _find_sql_connect_call(tree: ast.Module) -> ast.Call | None:
    """Find the `sql.connect(...)` (or `*.connect(...)`) call node."""
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        # Match `sql.connect(...)` / `databricks.sql.connect(...)` / `connect(...)`
        if isinstance(func, ast.Attribute) and func.attr == "connect":
            return node
        if isinstance(func, ast.Name) and func.id == "connect":
            return node
    return None


def _kwarg_value(call: ast.Call, name: str) -> ast.expr | None:
    for kw in call.keywords:
        if kw.arg == name:
            return kw.value
    return None


def _is_finite_numeric(node: ast.expr | None, *, max_value: float = 60.0) -> bool:
    """True if node is a numeric literal with 0 < value <= max_value."""
    if node is None:
        return False
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        v = float(node.value)
        return 0 < v <= max_value
    return False


def _find_retry_handler(tree: ast.Module) -> ast.ExceptHandler | None:
    """Find the retry-loop except handler (around line 30 of db.py)."""
    for node in ast.walk(tree):
        if isinstance(node, ast.ExceptHandler):
            return node
    return None


def _exception_names(handler: ast.ExceptHandler) -> set[str]:
    """Extract the names of exception classes the handler catches."""
    names: set[str] = set()
    type_node = handler.type
    if type_node is None:
        return names

    candidates: list[ast.expr]
    if isinstance(type_node, ast.Tuple):
        candidates = list(type_node.elts)
    else:
        candidates = [type_node]

    for c in candidates:
        if isinstance(c, ast.Name):
            names.add(c.id)
        elif isinstance(c, ast.Attribute):
            names.add(c.attr)
    return names


def test_sql_connect_has_socket_or_http_timeout() -> None:
    """sql.connect(...) MUST pass a finite _socket_timeout or http_timeout.

    Without it, a stuck Databricks SQL warehouse will hang the worker
    thread forever. STATEMENT_TIMEOUT in session_configuration only
    bounds query execution — it does not cover socket-level hangs
    during connection handshake or auth.
    """
    tree = _load_module()
    call = _find_sql_connect_call(tree)
    assert call is not None, "expected to find a sql.connect(...) call in app/db.py"

    socket_to = _kwarg_value(call, "_socket_timeout")
    http_to = _kwarg_value(call, "http_timeout")

    has_finite_timeout = _is_finite_numeric(socket_to) or _is_finite_numeric(http_to)
    assert has_finite_timeout, (
        "sql.connect(...) is missing a finite `_socket_timeout` or `http_timeout` "
        "kwarg (expected a numeric literal in (0, 60]). A stuck Databricks "
        "warehouse will hang the worker thread indefinitely. "
        "STATEMENT_TIMEOUT in session_configuration is NOT sufficient — it does "
        "not cover socket connect/auth hangs."
    )


def test_retry_handler_catches_transient_network_errors() -> None:
    """The retry except-clause must include at least one broad transient class.

    Catching only `ServerOperationError` / `OperationalError` leaves
    `ConnectionError` / `OSError` / socket timeouts uncaught — they
    bubble up on the first attempt and the retry never fires.
    """
    tree = _load_module()
    handler = _find_retry_handler(tree)
    assert handler is not None, "expected to find a try/except in app/db.py"

    caught = _exception_names(handler)
    broad = {"ConnectionError", "OSError", "TimeoutError", "Exception"}

    assert caught & broad, (
        f"retry handler catches only {sorted(caught)}; expected to also catch "
        f"at least one of {sorted(broad)} so transient network failures "
        f"(socket timeouts, dropped connections) trigger the retry instead "
        f"of bubbling up immediately."
    )
