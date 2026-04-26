"""Negative test: scripts/databricks/run_sql_file.py SQL splitter must respect
string literals and block comments (i.e. NOT use naive `.split(";")`).

The original splitter used a line-based `.endswith(";")` heuristic that broke
on semicolons embedded in single-quoted strings (`'a;b'`) and block comments
(`/* ; */`). This test imports the production `split_sql` function and asserts
correct statement counts on inputs that any sql-aware splitter handles. RED
until the script switches to a real SQL parser (sqlparse / sqlglot).
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

SCRIPT_PATH = (
    Path(__file__).resolve().parent.parent
    / "scripts"
    / "databricks"
    / "run_sql_file.py"
)


def _load_splitter():
    spec = importlib.util.spec_from_file_location("_run_sql_file_for_test", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules["_run_sql_file_for_test"] = mod
    spec.loader.exec_module(mod)
    return mod.split_sql


def test_splitter_respects_semicolon_inside_string_literal():
    """A `;` inside a single-quoted string must NOT terminate a statement.

    Naive split returns 3 (cuts at `'a;b'`), correct split returns 2.
    """
    split_sql = _load_splitter()
    sql = "INSERT INTO t VALUES ('a;b'); SELECT 1;"
    stmts = split_sql(sql)
    assert len(stmts) == 2, (
        f"expected 2 statements, got {len(stmts)}: {stmts!r} — splitter is "
        f"slicing inside a string literal"
    )
    assert "INSERT INTO t VALUES ('a;b')" in stmts[0], (
        f"first statement was mangled: {stmts[0]!r}"
    )


def test_splitter_respects_semicolon_inside_block_comment():
    """A `;` inside a /* ... */ block comment must NOT terminate a statement.

    Correct splitter: 1 statement. Naive splitter cuts at the comment-internal
    `;` and produces 2 chunks.
    """
    split_sql = _load_splitter()
    sql = "/* note ; here\n   still in comment ; */\nSELECT 1;"
    stmts = split_sql(sql)
    assert len(stmts) == 1, (
        f"expected 1 statement, got {len(stmts)}: {stmts!r} — splitter cut "
        f"inside a block comment"
    )


def test_splitter_handles_multiple_statements():
    """Sanity: a normal multi-statement file splits correctly."""
    split_sql = _load_splitter()
    sql = "CREATE TABLE a (id INT);\nCREATE TABLE b (id INT);\nINSERT INTO a VALUES (1);"
    stmts = split_sql(sql)
    assert len(stmts) == 3, f"expected 3 statements, got {len(stmts)}: {stmts!r}"
