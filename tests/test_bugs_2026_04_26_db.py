"""Negative regression tests for bugs #106, #107, #111 (db + schemas).

These tests encode the *desired* behaviour after the bug is fixed. They are
expected to FAIL while the bug is still present and flip GREEN after the fix.

  #106 — No connection pooling in app/db.py: every warehouse_query call opens
          a new sql.connect. Fix: expose a module-level pool singleton.

  #107 — Hardcoded 2 s sleep in retry path (app/db.py:47). Fix: compute sleep
          from the attempt index (e.g. 2 ** attempt) for exponential backoff.

  #111 — Float precision: Score = Field(ge=0.0, le=1.0) accepts the value
          1.0000000000000002 which is mathematically > 1.0. Fix: use a strict
          Annotated validator (e.g. AfterValidator) to reject it.
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def _parse(rel: str) -> ast.Module:
    return ast.parse(_read(rel), filename=rel)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _find_function(tree: ast.Module, name: str) -> ast.FunctionDef | ast.AsyncFunctionDef:
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return node
    raise AssertionError(f"function '{name}' not found in AST")


def _collect_constants(node: ast.AST) -> list[object]:
    """Return all literal constant values under *node*."""
    return [
        n.value
        for n in ast.walk(node)
        if isinstance(n, ast.Constant)
    ]


def _collect_calls(node: ast.AST, func_name: str) -> list[ast.Call]:
    """Return all Call nodes whose func resolves to *func_name*."""
    results = []
    for n in ast.walk(node):
        if not isinstance(n, ast.Call):
            continue
        fn = n.func
        # time.sleep(…) → Attribute
        if isinstance(fn, ast.Attribute) and fn.attr == func_name:
            results.append(n)
        # sleep(…) → Name
        elif isinstance(fn, ast.Name) and fn.id == func_name:
            results.append(n)
    return results


# ---------------------------------------------------------------------------
# Bug #106 — No connection pooling
# ---------------------------------------------------------------------------

class TestBug106NoConnectionPooling:
    """Assert that app/db.py exposes a module-level connection pool."""

    def test_module_has_pool_singleton(self) -> None:
        """app/db.py should define a module-level _pool or Pool variable."""
        tree = _parse("app/db.py")
        # Collect all top-level Assign / AnnAssign targets at module level
        # (depth-1 only — don't descend into functions).
        module_names: set[str] = set()
        for node in tree.body:
            if isinstance(node, ast.Assign):
                for t in node.targets:
                    if isinstance(t, ast.Name):
                        module_names.add(t.id)
            elif isinstance(node, (ast.AnnAssign,)):
                if isinstance(node.target, ast.Name):
                    module_names.add(node.target.id)

        has_pool = any(
            "_pool" in n or "pool" in n.lower()
            for n in module_names
        )
        assert has_pool, (
            "Bug #106: app/db.py does not expose a module-level connection pool.\n"
            f"Module-level names found: {sorted(module_names)}\n"
            "Fix: add a module-level singleton (e.g. `_pool = sql.ConnectionPool(...)`) "
            "and reuse it in warehouse_query()."
        )

    def test_warehouse_query_does_not_open_new_connect_every_call(self) -> None:
        """warehouse_query should not contain an unconditional sql.connect() call.

        With a pool, connection acquisition should go through the pool object,
        not through a bare sql.connect() inside the function body.
        """
        tree = _parse("app/db.py")
        fn = _find_function(tree, "warehouse_query")

        # Count sql.connect(…) calls inside the function body.
        connect_calls = [
            n for n in ast.walk(fn)
            if isinstance(n, ast.Call)
            and isinstance(n.func, ast.Attribute)
            and n.func.attr == "connect"
        ]

        assert len(connect_calls) == 0, (
            f"Bug #106: warehouse_query() still calls sql.connect() directly "
            f"({len(connect_calls)} time(s)).\n"
            "Fix: acquire the connection from the module-level pool instead."
        )


# ---------------------------------------------------------------------------
# Bug #107 — Hardcoded 2 s sleep (no exponential backoff)
# ---------------------------------------------------------------------------

class TestBug107HardcodedSleep:
    """Assert that the retry sleep in warehouse_query uses exponential backoff."""

    def test_sleep_is_not_a_hardcoded_literal(self) -> None:
        """time.sleep() inside warehouse_query must not be called with a bare int/float literal."""
        tree = _parse("app/db.py")
        fn = _find_function(tree, "warehouse_query")

        sleep_calls = _collect_calls(fn, "sleep")
        assert sleep_calls, (
            "warehouse_query has no sleep() call at all — "
            "check the file path or function name."
        )

        for call in sleep_calls:
            assert call.args, "sleep() called with no arguments?"
            arg = call.args[0]
            is_literal = isinstance(arg, ast.Constant) and isinstance(arg.value, (int, float))
            assert not is_literal, (
                f"Bug #107: time.sleep({arg.value if isinstance(arg, ast.Constant) else '?'}) "
                "is a hardcoded literal — no exponential backoff.\n"
                "Fix: use `time.sleep(2 ** attempt)` or equivalent."
            )

    def test_sleep_arg_references_attempt(self) -> None:
        """The sleep argument must reference the loop variable (attempt or similar)."""
        tree = _parse("app/db.py")
        fn = _find_function(tree, "warehouse_query")

        sleep_calls = _collect_calls(fn, "sleep")
        for call in sleep_calls:
            if not call.args:
                continue
            arg = call.args[0]
            # Collect all Name nodes inside the argument expression.
            names_in_arg = {n.id for n in ast.walk(arg) if isinstance(n, ast.Name)}
            # Also accept BinOp (e.g. 2 ** attempt) — at least one Name must appear.
            has_name = bool(names_in_arg)
            assert has_name, (
                "Bug #107: sleep() arg contains no variable reference — "
                "it cannot scale with retry count.\n"
                f"Arg AST: {ast.dump(arg)}\n"
                "Fix: `time.sleep(2 ** attempt)` or `time.sleep(min(30, 2 ** attempt))`."
            )

            # Confirm the name looks like an attempt counter.
            looks_like_attempt = any(
                "attempt" in n or "retry" in n or "backoff" in n
                for n in names_in_arg
            )
            assert looks_like_attempt, (
                f"Bug #107: sleep() arg references {names_in_arg} but none look like\n"
                "an attempt/retry counter. Exponential backoff must scale with the attempt.\n"
                "Fix: `time.sleep(2 ** attempt)`."
            )


# ---------------------------------------------------------------------------
# Bug #111 — Float precision: 1.0000000000000002 passes le=1.0 validator
# ---------------------------------------------------------------------------

class TestBug111FloatPrecision:
    """Assert that Pydantic rejects 1.0000000000000002 for a Field(le=1.0) score."""

    def test_ranked_hospital_rejects_score_above_one(self) -> None:
        """RankedHospital.specialty_match should reject 1.0000000000000002."""
        from pydantic import ValidationError  # noqa: PLC0415

        # Import the real schema — this is not a mock.
        try:
            from contracts.schemas import RankedHospital  # noqa: PLC0415
        except ImportError:
            pytest.skip("contracts.schemas not importable from test environment")

        too_large = 1.0 + 2e-16  # == 1.0000000000000002 in IEEE-754

        with pytest.raises(ValidationError, match=r"less than or equal"):
            RankedHospital(
                hospital_id="HOSP_PREC",
                name="Precision Test Hospital",
                travel_min=10,
                specialty_match=too_large,  # should be rejected
                cost_estimate_inr=1000,
                non_medical_cost_inr=100,
                lat=19.076,
                lon=72.877,
            )

    def test_pydantic_le_field_rejects_epsilon_above_one(self) -> None:
        """A standalone Field(le=1.0) model should reject 1.0 + 2e-16."""
        from pydantic import BaseModel, Field, ValidationError  # noqa: PLC0415

        class ScoreModel(BaseModel):
            score: float = Field(ge=0.0, le=1.0)

        too_large = 1.0 + 2e-16  # IEEE-754: evaluates to 1.0000000000000002

        # This assertion documents bug #111: currently Pydantic's le= does a
        # standard float comparison which passes for this value because of
        # floating-point rounding. The test should fail today and pass after
        # the fix (e.g. using AfterValidator with Decimal comparison).
        with pytest.raises(ValidationError):
            ScoreModel(score=too_large)
