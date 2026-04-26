"""
Negative test: scripts/databricks/llm_trust.py uses temperature=0.1 in the
LLM payload, which makes trust scores non-deterministic across runs.

For a "Trust Scorer" we want either:
  - temperature == 0 (literal int 0 / float 0.0), OR
  - an explicit `seed=...` parameter alongside.

Currently the script ships with temperature=0.1 and no seed -> RED.

Bonus assertion: open(OUT, "w", ...) must pass encoding="utf-8" so Hindi
facility names round-trip on non-UTF locales. Currently it does not -> RED.

AST-only. No Databricks calls, no network, no env vars required.
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
TARGET = REPO_ROOT / "scripts" / "databricks" / "llm_trust.py"


def _load_tree() -> tuple[ast.Module, list[str]]:
    src = TARGET.read_text(encoding="utf-8")
    return ast.parse(src, filename=str(TARGET)), src.splitlines()


def _is_zero_literal(node: ast.AST) -> bool:
    """Return True iff node is the literal int 0 or float 0.0."""
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        # exclude bools (True/False are int subclasses in Python)
        if isinstance(node.value, bool):
            return False
        return float(node.value) == 0.0
    return False


def _walk_dict_for_key(dict_node: ast.Dict, key_name: str) -> ast.AST | None:
    """Find the value for a string key inside an ast.Dict literal."""
    for k, v in zip(dict_node.keys, dict_node.values):
        if isinstance(k, ast.Constant) and k.value == key_name:
            return v
    return None


def _collect_temperature_sites(tree: ast.Module) -> list[tuple[int, ast.AST]]:
    """
    Find every place that sets a `temperature` value in this script.
    Covers:
      - kwargs on any call: foo(..., temperature=X, ...)
      - dict literals: {"temperature": X} (e.g. inside json.dumps payloads)
    Returns list of (lineno, value_node).
    """
    sites: list[tuple[int, ast.AST]] = []
    for node in ast.walk(tree):
        # kwargs on Calls
        if isinstance(node, ast.Call):
            for kw in node.keywords:
                if kw.arg == "temperature":
                    sites.append((kw.value.lineno, kw.value))
        # dict literals with a "temperature" string key
        if isinstance(node, ast.Dict):
            v = _walk_dict_for_key(node, "temperature")
            if v is not None:
                sites.append((v.lineno, v))
    return sites


def _has_seed_kwarg_or_key(tree: ast.Module) -> bool:
    """Heuristic: does any call kwarg or dict key named 'seed' exist?"""
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            for kw in node.keywords:
                if kw.arg == "seed":
                    return True
        if isinstance(node, ast.Dict):
            if _walk_dict_for_key(node, "seed") is not None:
                return True
    return False


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_target_file_exists():
    """Sanity: the script under audit must be present."""
    assert TARGET.exists(), f"missing target file: {TARGET}"


def test_llm_temperature_is_deterministic():
    """
    The Trust Scorer must use temperature=0 (or pair non-zero with an explicit
    seed). Any non-zero temperature without seed is a determinism bug:
    re-running the same hospital yields different trust scores, breaking
    reproducibility of the bronze->silver->gold trust pipeline.
    """
    tree, lines = _load_tree()
    sites = _collect_temperature_sites(tree)

    assert sites, (
        f"AST scan found NO `temperature=...` setting in {TARGET}. "
        f"Either the file changed shape (update this test) or temperature "
        f"is no longer being set explicitly."
    )

    has_seed = _has_seed_kwarg_or_key(tree)

    bad: list[str] = []
    for lineno, value_node in sites:
        if _is_zero_literal(value_node):
            continue
        if has_seed:
            # non-zero temperature is OK iff a seed is also passed somewhere
            continue
        # build a clear file:line message with the offending source line
        try:
            src_line = lines[lineno - 1].strip()
        except IndexError:
            src_line = "<line out of range>"
        bad.append(f"{TARGET}:{lineno} -> {src_line}")

    assert not bad, (
        "LLM trust scorer is non-deterministic: temperature is non-zero and "
        "no `seed=` is passed. Set temperature=0 (or add a seed) at:\n  "
        + "\n  ".join(bad)
    )


def test_results_file_opened_with_utf8_encoding():
    """
    The script writes JSONL containing Hindi facility names. On a non-UTF
    locale (e.g. POSIX/C) Python's default text encoding is ASCII and
    json.dumps with the default ensure_ascii=True still escapes, BUT any
    later refactor that drops ensure_ascii will mangle names. Make the
    contract explicit: open(..., encoding="utf-8").
    """
    tree, lines = _load_tree()

    open_calls: list[ast.Call] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        is_open = (
            (isinstance(func, ast.Name) and func.id == "open")
            or (isinstance(func, ast.Attribute) and func.attr == "open")
        )
        if not is_open:
            continue
        # restrict to write-mode opens: 2nd positional arg starts with "w",
        # or mode kwarg starts with "w"
        mode_val: str | None = None
        if len(node.args) >= 2 and isinstance(node.args[1], ast.Constant):
            if isinstance(node.args[1].value, str):
                mode_val = node.args[1].value
        for kw in node.keywords:
            if kw.arg == "mode" and isinstance(kw.value, ast.Constant):
                if isinstance(kw.value.value, str):
                    mode_val = kw.value.value
        if mode_val is None or not mode_val.startswith("w"):
            continue
        open_calls.append(node)

    assert open_calls, (
        f"AST scan found NO write-mode open() in {TARGET}. "
        f"Update this test if the file layout changed."
    )

    missing: list[str] = []
    for call in open_calls:
        has_encoding = any(kw.arg == "encoding" for kw in call.keywords)
        if not has_encoding:
            try:
                src_line = lines[call.lineno - 1].strip()
            except IndexError:
                src_line = "<line out of range>"
            missing.append(f"{TARGET}:{call.lineno} -> {src_line}")

    assert not missing, (
        "open(..., 'w') without encoding=\"utf-8\" — Hindi facility names "
        "will mangle on non-UTF locales. Fix at:\n  "
        + "\n  ".join(missing)
    )


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-x", "-vv"]))
