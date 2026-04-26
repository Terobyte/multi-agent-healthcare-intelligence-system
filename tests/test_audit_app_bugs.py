"""
Audit-driven failing tests for app/ package.

Each test documents a real bug found during code review.
Tests are designed to FAIL on current code and PASS once the bug is fixed.
Bug 5 is a regression-protection test (intentional behavior) — it should PASS on current code.
"""

import importlib
import os
import time
import warnings
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# BUG 1 — settings.py does not forward DATABRICKS_WAREHOUSE_ID to os.environ
# ---------------------------------------------------------------------------

def test_settings_forwards_warehouse_id_to_environ(tmp_path):
    """
    Bug: app/settings.py forwards HOST and TOKEN via os.environ.setdefault but
    omits DATABRICKS_WAREHOUSE_ID. The databricks-sdk reads this key from
    os.environ at runtime, so a .env-only deployment leaves it unset for
    downstream SDK calls that don't accept it as an explicit parameter.

    Test isolates a fresh Python process with its own .env in tmp_path so the
    forwarding behaviour can be observed independently of the project's real
    .env file.
    """
    import subprocess
    import sys
    from pathlib import Path

    project_root = Path(__file__).resolve().parent.parent
    sentinel = "wh_forward_sentinel_xyz"

    (tmp_path / ".env").write_text(
        "DATABRICKS_HOST=https://test.cloud.databricks.com\n"
        "DATABRICKS_TOKEN=dapi-test-token-not-real\n"
        f"DATABRICKS_WAREHOUSE_ID={sentinel}\n"
    )

    code = (
        "import os, sys\n"
        f"sys.path.insert(0, {repr(str(project_root))})\n"
        # strip env so .env is the only source — observable forwarding
        'for k in ("DATABRICKS_HOST", "DATABRICKS_TOKEN", "DATABRICKS_WAREHOUSE_ID"):\n'
        "    os.environ.pop(k, None)\n"
        "from app.settings import settings  # noqa: F401\n"
        'print(os.environ.get("DATABRICKS_WAREHOUSE_ID", "MISSING"))\n'
    )

    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=str(tmp_path),
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, (
        f"settings import crashed: stdout={result.stdout!r} stderr={result.stderr!r}"
    )
    assert sentinel in result.stdout, (
        "settings.py must forward DATABRICKS_WAREHOUSE_ID to os.environ "
        "alongside HOST and TOKEN. "
        f"Got os.environ['DATABRICKS_WAREHOUSE_ID'] = {result.stdout.strip()!r}"
    )


# ---------------------------------------------------------------------------
# BUG 2 — class Config: env_file triggers PydanticDeprecatedSince20 warning
# ---------------------------------------------------------------------------

def test_settings_uses_modern_settingsconfigdict_not_legacy_class_config():
    """
    Bug: app/settings.py uses the pydantic v1 `class Config: env_file = ".env"`
    pattern inside a pydantic-settings v2 BaseSettings subclass. With
    pydantic-settings >= 2.1 this triggers a PydanticDeprecatedSince20 warning.
    The fix is to replace it with `model_config = SettingsConfigDict(env_file=".env")`.
    """
    import app.settings  # noqa: F401 — ensure module exists before reload

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        importlib.reload(app.settings)

    pydantic_deprecation_msgs = [
        str(w.message)
        for w in caught
        if (
            "pydantic" in w.category.__name__.lower()
            or "class-based" in str(w.message).lower()
            or "configdict" in str(w.message).lower()
            or "DeprecatedSince" in w.category.__name__
        )
    ]

    assert not pydantic_deprecation_msgs, (
        "app/settings.py uses deprecated `class Config:` instead of "
        "`model_config = SettingsConfigDict(...)`. "
        f"Warnings captured: {pydantic_deprecation_msgs}"
    )


# ---------------------------------------------------------------------------
# BUG 3 — /health must expose a clean boolean `fm_ok` for monitors and treat
#          empty endpoint list (count=0) as degraded, not ok
# ---------------------------------------------------------------------------

def test_health_response_includes_fm_ok_signal_and_treats_empty_as_degraded():
    """
    Block 9 spec retains `fm_endpoints: N` in the response (N >= 1 expected
    against our actual workspace). Audit added a parallel `fm_ok` boolean so
    dashboards/alerts can monitor without parsing an int.

    Two checks here:
      (a) `fm_ok` must be present in the response body.
      (b) When the FM API returns an empty list (N=0), status must be
          `degraded`, not `ok` — empty endpoints means misconfig, not health.
    """
    from fastapi.testclient import TestClient

    # case (a): healthy with non-empty endpoints
    with patch("mlflow.deployments.get_deploy_client") as mock_get_client:
        fake_client = MagicMock()
        fake_client.list_endpoints.return_value = ["ep1", "ep2"]
        mock_get_client.return_value = fake_client

        import app.main
        importlib.reload(app.main)

        client = TestClient(app.main.app)
        body_ok = client.get("/health").json()

    assert "fm_ok" in body_ok, "/health must expose a boolean `fm_ok` for monitoring"
    assert body_ok["fm_ok"] is True, "fm_ok must be True when endpoints > 0"
    assert body_ok["status"] == "ok"

    # case (b): empty endpoint list → degraded
    with patch("mlflow.deployments.get_deploy_client") as mock_get_client:
        fake_client = MagicMock()
        fake_client.list_endpoints.return_value = []
        mock_get_client.return_value = fake_client

        importlib.reload(app.main)

        client = TestClient(app.main.app)
        body_empty = client.get("/health").json()

    assert body_empty["status"] == "degraded", (
        "fm_endpoints=0 must report `degraded` (FM reachable but no endpoints provisioned)"
    )
    assert body_empty["fm_ok"] is False


# ---------------------------------------------------------------------------
# BUG 4 — warehouse[:8] + "..." mask is broken for short / empty warehouse_id
# ---------------------------------------------------------------------------

def test_health_warehouse_mask_does_not_reveal_short_ids(monkeypatch):
    """
    Bug: app/main.py line 46 builds the warehouse mask as
    `settings.databricks_warehouse_id[:8] + "..."`.
    For a warehouse_id shorter than 8 chars (e.g. "abc") the full ID is
    exposed: "abc...". For an empty string the output is "..." which is
    misleading. A proper mask should always redact part or all of the ID.
    """
    short_id = "abc"
    monkeypatch.setenv("DATABRICKS_WAREHOUSE_ID", short_id)
    monkeypatch.setenv("DATABRICKS_HOST", "https://test.cloud.databricks.com")
    monkeypatch.setenv("DATABRICKS_TOKEN", "dapi-test-token-not-real")

    with patch("mlflow.deployments.get_deploy_client") as mock_get_client:
        fake_client = MagicMock()
        fake_client.list_endpoints.return_value = []
        mock_get_client.return_value = fake_client

        import app.settings
        import app.main
        importlib.reload(app.settings)
        importlib.reload(app.main)

        client = __import__("fastapi.testclient", fromlist=["TestClient"]).TestClient
        tc = client(app.main.app)
        r = tc.get("/health")

    body = r.json()
    warehouse_field = body.get("warehouse", "")
    assert short_id not in warehouse_field, (
        f"warehouse mask exposes full short ID '{short_id}' as '{warehouse_field}'. "
        "The [:8]+... pattern is broken for IDs shorter than 8 characters."
    )


# ---------------------------------------------------------------------------
# BUG 5 — fm_endpoint_count does NOT retry within TTL after failure
#          (regression-protection — this test PASSES on current code)
# ---------------------------------------------------------------------------

def test_fm_endpoint_count_does_not_retry_within_ttl_after_failure(monkeypatch):
    """
    Regression-protection (intentional behaviour), not a bug.

    After _fm_endpoint_count() fails, it stamps _ep_cache["ts"] to `now`.
    For the next TTL seconds any probe returns the cached None without
    calling the FM API again — preventing a retry storm when FM is down.
    After the TTL expires the next call does retry.

    This test SHOULD PASS on current code. If it starts failing, someone
    changed the cache-stamp-on-failure behaviour unintentionally.
    """
    import app.main as m

    # reset module-level cache
    m._ep_cache["n"] = None
    m._ep_cache["ts"] = 0.0
    m.fm_client.cache_clear()

    call_count = {"n": 0}

    class FakeEndpoints:
        def list_endpoints(self):
            call_count["n"] += 1
            if call_count["n"] == 1:
                raise RuntimeError("simulated FM cold start")
            return ["ep1", "ep2"]

    fake = FakeEndpoints()
    monkeypatch.setattr(m, "fm_client", lambda: fake)

    time_seq = [1000.0, 1010.0, 1070.0]

    def fake_time():
        return time_seq.pop(0)

    monkeypatch.setattr(time, "time", fake_time)

    # First call: fails, stamps ts=1000, returns None
    result1 = m._fm_endpoint_count()
    assert result1 is None, "first call should return None on failure"

    # Second call at t=1010 (within 60s TTL): must NOT retry
    result2 = m._fm_endpoint_count()
    assert result2 is None, "within TTL after failure, should still return cached None"
    assert call_count["n"] == 1, (
        f"expected exactly 1 upstream call within TTL, got {call_count['n']}"
    )

    # Third call at t=1070 (past TTL): must retry and succeed
    result3 = m._fm_endpoint_count()
    assert result3 == 2, f"after TTL, should retry and return count=2, got {result3}"
    assert call_count["n"] == 2, (
        f"expected 2 upstream calls total after TTL retry, got {call_count['n']}"
    )


# ---------------------------------------------------------------------------
# BUG 6 — fm_client() lru_cache has no public invalidation path
# ---------------------------------------------------------------------------

def test_fm_client_cache_can_be_invalidated_for_token_rotation():
    """
    Bug: app/main.py decorates fm_client() with @lru_cache(maxsize=1).
    After a Databricks token rotation the cached client holds stale credentials
    forever (until process restart). There is no app-level reset function or
    admin endpoint that operators can call to force re-initialisation.
    The fix is to expose `reset_fm_client()` or `invalidate_fm_client()`.
    This test FAILS on current code because no such function exists.
    """
    import app.main as m

    has_reset = hasattr(m, "reset_fm_client") or hasattr(m, "invalidate_fm_client")
    assert has_reset, (
        "app/main.py has no public reset/invalidate function for the fm_client "
        "lru_cache. After token rotation the cached client silently uses stale "
        "credentials. Add `def reset_fm_client(): fm_client.cache_clear()` "
        "(or equivalent) so operators can trigger re-authentication without "
        "a full process restart."
    )
