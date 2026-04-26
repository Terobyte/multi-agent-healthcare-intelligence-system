"""Regression tests for two known bugs in Databricks-side scripts.

Bug A: mubarak/triage/01_symptom_corpus.py uses tempfile.mktemp() (deprecated,
       race-prone, file is never cleaned up — leaks on every run).

Bug B: scripts/databricks/llm_trust.py:parse_response uses naive
       text.index("{") / text.rindex("}") to slice JSON out of LLM responses.
       Any brace inside reasoning text before the real JSON corrupts the slice.
"""
from __future__ import annotations

import ast
import importlib.util
import sys
import tempfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SYMPTOM_CORPUS_SCRIPT = REPO_ROOT / "mubarak" / "triage" / "01_symptom_corpus.py"
LLM_TRUST_SCRIPT = REPO_ROOT / "scripts" / "databricks" / "llm_trust.py"


# ── Bug A ────────────────────────────────────────────────────────────────────

def _collect_tempfile_calls(tree: ast.AST) -> list[str]:
    """Return every attribute name called against the `tempfile` module."""
    calls: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if (
            isinstance(func, ast.Attribute)
            and isinstance(func.value, ast.Name)
            and func.value.id == "tempfile"
        ):
            calls.append(func.attr)
    return calls


def test_bug_symptom_corpus_does_not_leak_tempfile():
    """01_symptom_corpus.py must not use the deprecated, leak-prone tempfile.mktemp().

    Acceptable replacements: NamedTemporaryFile, TemporaryDirectory, mkstemp.
    """
    assert SYMPTOM_CORPUS_SCRIPT.is_file(), f"missing script: {SYMPTOM_CORPUS_SCRIPT}"
    source = SYMPTOM_CORPUS_SCRIPT.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(SYMPTOM_CORPUS_SCRIPT))

    tempfile_calls = _collect_tempfile_calls(tree)
    assert "mktemp" not in tempfile_calls, (
        f"{SYMPTOM_CORPUS_SCRIPT} uses tempfile.mktemp() — deprecated, race-prone, "
        f"and the resulting parquet file is never cleaned up (leaks per run). "
        f"Use tempfile.NamedTemporaryFile(delete=True, suffix='.parquet') or "
        f"tempfile.TemporaryDirectory() instead. "
        f"All tempfile.* calls found: {tempfile_calls}"
    )


# ── Bug B ────────────────────────────────────────────────────────────────────

def _load_parse_response():
    """Extract just the `parse_response` function source from llm_trust.py and
    materialize it as an importable module — avoids running the script's
    top-level Databricks-CLI code path.
    """
    assert LLM_TRUST_SCRIPT.is_file(), f"missing script: {LLM_TRUST_SCRIPT}"
    source = LLM_TRUST_SCRIPT.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(LLM_TRUST_SCRIPT))

    # Keep only imports and function/class defs — drop the top-level script body.
    safe_nodes = [
        n for n in tree.body
        if isinstance(n, (ast.Import, ast.ImportFrom, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
    ]
    safe_module_src = ast.unparse(ast.Module(body=safe_nodes, type_ignores=[]))

    tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix="_llm_trust_isolated.py", delete=False, encoding="utf-8"
    )
    try:
        tmp.write(safe_module_src)
        tmp.flush()
        tmp.close()
        spec = importlib.util.spec_from_file_location("llm_trust_isolated", tmp.name)
        module = importlib.util.module_from_spec(spec)
        sys.modules["llm_trust_isolated"] = module
        spec.loader.exec_module(module)
        fn = getattr(module, "parse_response", None)
        assert callable(fn), "parse_response not found in llm_trust.py"
        return fn
    finally:
        Path(tmp.name).unlink(missing_ok=True)


def test_bug_llm_trust_parse_handles_brace_in_reasoning_text():
    """parse_response must extract the real JSON object even when reasoning
    text before it contains stray braces (e.g. a math notation like {0,1}).

    Buggy implementation does text.index("{") which latches onto the '{0,1}'
    brace and yields a corrupted slice that fails json.loads.
    """
    parse_response = _load_parse_response()

    response = (
        "The score range is {0,1}. Final answer: "
        '{"p_bed": 0.7, "p_oxygen": 0.6, "p_drug": 0.5, '
        '"p_specialist": 0.4, "ci": 0.1, "reasoning": "ok"}'
    )

    parsed = parse_response(response)

    assert "_error" not in parsed, (
        f"parse_response failed on response with brace in reasoning text: {parsed}"
    )
    assert parsed.get("p_bed") == pytest.approx(0.7), (
        f"expected p_bed=0.7, got {parsed!r} — naive text.index('{{') latched "
        f"onto the '{{0,1}}' brace in the reasoning prefix and corrupted the slice"
    )
    assert parsed.get("p_oxygen") == pytest.approx(0.6)
    assert parsed.get("reasoning") == "ok"
