"""Audit-driven failing tests for repo-level config files and scripts/databricks/smoke_test.py.

Each test is written to FAIL on current code and PASS after the underlying bug is fixed.
Bugs covered:
  A - .env.example contains real warehouse ID 10fff96dd6d936b5
  B - .gitignore missing __pycache__/ and *.pyc
  C - .gitignore missing .env.* glob / explicit .env.production/.env.staging
  D - smoke_test.py never calls sys.exit(1) on failure (AST + subprocess)
  E - smoke_test.py calls json.loads outside a try/except
  F - requirements.txt uses full mlflow instead of mlflow-skinny
  G - requirements.txt has no upper version bounds on any dependency
"""


# ---------------------------------------------------------------------------
# BUG A — .env.example contains real warehouse ID 10fff96dd6d936b5
# ---------------------------------------------------------------------------

def test_env_example_does_not_contain_real_warehouse_id():
    """.env.example must use placeholder, not real warehouse ID 10fff96dd6d936b5."""
    from pathlib import Path
    ROOT = Path(__file__).resolve().parent.parent
    content = (ROOT / ".env.example").read_text()
    assert "10fff96dd6d936b5" not in content, (
        ".env.example has real warehouse ID hardcoded — replace with `<warehouse-id>` placeholder"
    )
    # also check it has a placeholder pattern
    assert "<" in content and ">" in content, \
        ".env.example should use <placeholder> style (e.g., <warehouse-id>)"


# ---------------------------------------------------------------------------
# BUG B — .gitignore missing __pycache__/ and *.pyc
# ---------------------------------------------------------------------------

def test_gitignore_excludes_python_cache_dirs():
    """.gitignore must exclude __pycache__/ and *.pyc to prevent accidental commits."""
    from pathlib import Path
    ROOT = Path(__file__).resolve().parent.parent
    content = (ROOT / ".gitignore").read_text()
    assert "__pycache__" in content, ".gitignore must exclude __pycache__/ to prevent accidental commits"
    assert "*.pyc" in content or "*.py[cod]" in content, ".gitignore should exclude *.pyc"


# ---------------------------------------------------------------------------
# BUG C — .gitignore does not cover all .env.* variants
# ---------------------------------------------------------------------------

def test_gitignore_covers_all_env_file_variants():
    """.gitignore must cover .env.* glob or explicit .env.production/.env.staging."""
    from pathlib import Path
    ROOT = Path(__file__).resolve().parent.parent
    content = (ROOT / ".gitignore").read_text()
    # at least one of: a glob `.env.*` OR explicit listings of common variants
    has_glob = ".env.*" in content
    explicit_variants = all(v in content for v in [".env.production", ".env.staging"])
    assert has_glob or explicit_variants, (
        ".gitignore should cover .env.* glob or explicit .env.production/.env.staging variants"
    )


# ---------------------------------------------------------------------------
# BUG D (a) — smoke_test.py never calls sys.exit(1) — AST inspection
# ---------------------------------------------------------------------------

def test_smoke_test_propagates_failure_via_exit_code_in_source():
    """smoke_test.py must call sys.exit(1) (or non-zero) on FAILED query."""
    import ast
    from pathlib import Path
    ROOT = Path(__file__).resolve().parent.parent
    src = (ROOT / "scripts" / "databricks" / "smoke_test.py").read_text()
    tree = ast.parse(src)
    # look for sys.exit with a non-zero argument anywhere in module
    has_nonzero_exit = False
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            is_sys_exit = (
                (isinstance(func, ast.Attribute) and func.attr == "exit"
                 and isinstance(func.value, ast.Name) and func.value.id == "sys")
                or (isinstance(func, ast.Name) and func.id == "exit")
            )
            if is_sys_exit and node.args:
                arg = node.args[0]
                if isinstance(arg, ast.Constant) and arg.value not in (0, None):
                    has_nonzero_exit = True
                elif not isinstance(arg, ast.Constant):
                    # variable / expression — assume could be non-zero
                    has_nonzero_exit = True
    assert has_nonzero_exit, (
        "smoke_test.py never calls sys.exit(1) — failures are silent under `set -e`"
    )


# ---------------------------------------------------------------------------
# BUG D (b) — smoke_test.py never calls sys.exit(1) — subprocess integration
# ---------------------------------------------------------------------------

def test_smoke_test_returns_nonzero_when_databricks_cli_fails(tmp_path, monkeypatch):
    """smoke_test.py must exit non-zero when databricks CLI errors out."""
    import subprocess
    import sys
    import os
    from pathlib import Path
    ROOT = Path(__file__).resolve().parent.parent

    # create a fake `databricks` shim that always exits 1 with empty stdout
    fake_bin = tmp_path / "fakebin"
    fake_bin.mkdir()
    fake_databricks = fake_bin / "databricks"
    fake_databricks.write_text("#!/bin/sh\necho '' >&2\nexit 1\n")
    fake_databricks.chmod(0o755)

    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}:{env['PATH']}"
    env["DBX_PROFILE"] = "tero2"
    env["DBX_WH"] = "fake_wh"

    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "databricks" / "smoke_test.py")],
        env=env, capture_output=True, text=True, timeout=60,
    )
    assert result.returncode != 0, (
        f"smoke_test.py exited 0 despite databricks CLI failing. "
        f"stdout: {result.stdout[:500]}, stderr: {result.stderr[:500]}"
    )


# ---------------------------------------------------------------------------
# BUG E — smoke_test.py calls json.loads outside a try/except
# ---------------------------------------------------------------------------

def test_smoke_test_handles_non_json_cli_output_gracefully():
    """smoke_test.py must wrap json.loads in try/except for resilience."""
    import ast
    from pathlib import Path
    ROOT = Path(__file__).resolve().parent.parent
    src = (ROOT / "scripts" / "databricks" / "smoke_test.py").read_text()
    tree = ast.parse(src)
    # find every call to json.loads — assert at least one is inside a Try
    json_loads_in_try = False
    for tnode in ast.walk(tree):
        if isinstance(tnode, ast.Try):
            for sub in ast.walk(tnode):
                if isinstance(sub, ast.Call):
                    f = sub.func
                    if (isinstance(f, ast.Attribute) and f.attr == "loads"
                        and isinstance(f.value, ast.Name) and f.value.id == "json"):
                        json_loads_in_try = True
                        break
    assert json_loads_in_try, (
        "smoke_test.py calls json.loads outside a try/except — non-JSON CLI output crashes the script"
    )


# ---------------------------------------------------------------------------
# BUG F — requirements.txt uses full mlflow instead of mlflow-skinny
# ---------------------------------------------------------------------------

def test_requirements_uses_mlflow_skinny_for_lightweight_deploy():
    """mlflow.deployments doesn't need full mlflow — use mlflow-skinny to cut Render cold-start."""
    from pathlib import Path
    ROOT = Path(__file__).resolve().parent.parent
    lines = (ROOT / "requirements.txt").read_text().splitlines()
    # skip lines starting with "mlflow-skinny", check if "mlflow" without "-skinny" is present
    has_full_mlflow = any(
        line.strip().startswith("mlflow") and not line.strip().startswith("mlflow-skinny")
        and not line.strip().startswith("#")
        for line in lines
    )
    assert not has_full_mlflow, (
        "requirements.txt has full `mlflow` — replace with `mlflow-skinny` "
        "since only `mlflow.deployments` is used (saves ~110MB transitive)"
    )


# ---------------------------------------------------------------------------
# BUG G — requirements.txt has no upper version bounds
# ---------------------------------------------------------------------------

def test_requirements_pin_upper_bounds_for_reproducibility():
    """Each runtime dep should have an upper bound to prevent surprise major bumps."""
    from pathlib import Path
    ROOT = Path(__file__).resolve().parent.parent
    bad = []
    for line in (ROOT / "requirements.txt").read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "<" not in line and "==" not in line:
            bad.append(line)
    assert not bad, f"deps without upper bound: {bad}"
