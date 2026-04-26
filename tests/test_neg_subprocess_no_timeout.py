"""Negative test: scripts under scripts/databricks/ must pass `timeout=` to subprocess.run.

Without `timeout=`, an expired Databricks token (or a CLI hang) leaves the script
blocked indefinitely on `subprocess.run(...)`. This test parses each source file
with `ast` and asserts every `subprocess.run(...)` (or bare `run(...)` aliased
from subprocess) has a `timeout` keyword argument. It also flags direct `Popen(...)`
constructions that lack `timeout=`.

Currently RED — the four scripts all call subprocess.run without a timeout.
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

REPO_ROOT = Path("/Users/terobyte/Desktop/Projects/Active/ai_hack/healthcare")
DBX_DIR = REPO_ROOT / "scripts" / "databricks"

TARGET_FILES = [
    DBX_DIR / "smoke_test.py",
    DBX_DIR / "dbq.py",
    DBX_DIR / "run_sql_file.py",
    DBX_DIR / "validate_invariants.py",
]


def _resolve_call_name(func: ast.expr) -> str:
    """Return a dotted name for a Call.func node, or '' if it can't be resolved.

    Handles `subprocess.run`, `subprocess.Popen`, bare `run`/`Popen` (when imported
    via `from subprocess import run`), and arbitrary attribute chains like
    `sp.run` where `sp` is an alias.
    """
    if isinstance(func, ast.Attribute):
        parts = []
        cur: ast.expr = func
        while isinstance(cur, ast.Attribute):
            parts.append(cur.attr)
            cur = cur.value
        if isinstance(cur, ast.Name):
            parts.append(cur.id)
        return ".".join(reversed(parts))
    if isinstance(func, ast.Name):
        return func.id
    return ""


def _is_subprocess_run_call(call: ast.Call, subprocess_aliases: set[str], run_aliases: set[str]) -> bool:
    name = _resolve_call_name(call.func)
    if not name:
        return False
    # subprocess.run, sp.run, my_subprocess.run, ...
    if name.endswith(".run"):
        head = name.rsplit(".", 1)[0]
        if head in subprocess_aliases:
            return True
    # bare `run(...)` from `from subprocess import run`
    if name in run_aliases:
        return True
    return False


def _is_popen_call(call: ast.Call, subprocess_aliases: set[str], popen_aliases: set[str]) -> bool:
    name = _resolve_call_name(call.func)
    if not name:
        return False
    if name.endswith(".Popen"):
        head = name.rsplit(".", 1)[0]
        if head in subprocess_aliases:
            return True
    if name in popen_aliases:
        return True
    return False


def _collect_aliases(tree: ast.AST) -> tuple[set[str], set[str], set[str]]:
    """Walk imports and collect names that refer to the subprocess module / its
    `run` / `Popen` symbols."""
    subprocess_aliases: set[str] = set()
    run_aliases: set[str] = set()
    popen_aliases: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "subprocess":
                    subprocess_aliases.add(alias.asname or "subprocess")
        elif isinstance(node, ast.ImportFrom):
            if node.module == "subprocess":
                for alias in node.names:
                    if alias.name == "run":
                        run_aliases.add(alias.asname or "run")
                    elif alias.name == "Popen":
                        popen_aliases.add(alias.asname or "Popen")
    return subprocess_aliases, run_aliases, popen_aliases


def _has_timeout_kwarg(call: ast.Call) -> bool:
    for kw in call.keywords:
        # **kwargs spreads can't be statically verified — treat them as missing
        if kw.arg == "timeout":
            return True
    return False


def _find_offending_calls(path: Path) -> list[tuple[str, int, str]]:
    """Return list of (file, lineno, kind) for each subprocess.run/Popen call
    missing a `timeout=` kwarg in the given source file."""
    src = path.read_text()
    tree = ast.parse(src, filename=str(path))
    sp_aliases, run_aliases, popen_aliases = _collect_aliases(tree)

    offenders: list[tuple[str, int, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if _is_subprocess_run_call(node, sp_aliases, run_aliases):
            if not _has_timeout_kwarg(node):
                offenders.append((str(path), node.lineno, "subprocess.run"))
        elif _is_popen_call(node, sp_aliases, popen_aliases):
            if not _has_timeout_kwarg(node):
                offenders.append((str(path), node.lineno, "subprocess.Popen"))
    return offenders


@pytest.mark.parametrize("source_path", TARGET_FILES, ids=lambda p: p.name)
def test_subprocess_run_has_timeout(source_path: Path) -> None:
    """Each subprocess.run(...) call in the file must include a `timeout=` kwarg.

    Rationale: an expired Databricks token / a stalled CLI invocation will hang
    forever without one, which is unacceptable for demo / CI scripts.
    """
    assert source_path.exists(), f"missing source file: {source_path}"
    offenders = _find_offending_calls(source_path)
    if offenders:
        pretty = "\n".join(f"  {f}:{ln}  ({kind} without timeout=)" for f, ln, kind in offenders)
        pytest.fail(
            f"{source_path.name}: {len(offenders)} subprocess call(s) without timeout=:\n{pretty}"
        )


def test_aggregate_no_subprocess_call_without_timeout() -> None:
    """Aggregate view: zero offending calls across all four scripts/databricks files."""
    all_offenders: list[tuple[str, int, str]] = []
    for path in TARGET_FILES:
        assert path.exists(), f"missing source file: {path}"
        all_offenders.extend(_find_offending_calls(path))

    if all_offenders:
        pretty = "\n".join(f"  {f}:{ln}  ({kind})" for f, ln, kind in all_offenders)
        pytest.fail(
            f"{len(all_offenders)} subprocess call(s) without timeout= across "
            f"scripts/databricks/:\n{pretty}"
        )
