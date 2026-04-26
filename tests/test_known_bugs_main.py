"""Regression locks for confirmed bugs in app/main.py (route layer).

Each test below is intended to FAIL on the current code so that committing it
locks in the regression. When a bug is fixed, the corresponding test must flip
from RED to GREEN.

Bugs covered:
  - health-cache: /health caches a failure for 60s and serves stale "degraded"
    even after Databricks recovers. Correct behaviour: on failure, do NOT
    bump the cache timestamp — let the next probe retry immediately.
  - demo-key auth matrix: re-verify all 4 (DEMO_KEY set/unset) x
    (AAROGYANET_DEV on/off) combinations behave per spec.
"""
import importlib
import os

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def _allow_dev_salt(monkeypatch):
    # Default to dev mode like the other test modules; individual tests below
    # override this when they need production-like semantics.
    monkeypatch.setenv("AAROGYANET_DEV", "1")


# --------------------------------------------------------------------------- #
# BUG A — /health cache stores failure ts and serves stale "degraded" 60s     #
# --------------------------------------------------------------------------- #
# app/main.py:159-170 (`_fm_endpoint_count`):
#   try:
#       _ep_cache["n"] = future.result(timeout=timeout)
#   except Exception:
#       logger.warning(...)
#   _ep_cache["ts"] = now    # <-- runs even on failure
# Effect: a single transient list_endpoints() failure pins /health into a
# "degraded" response for the full 60s ttl, even after Databricks recovers.
# Correct: bump _ep_cache["ts"] only on success — failures should leave the
# cache untouched so the next probe retries.
def test_bug_health_cache_does_not_serve_stale_failure_after_recovery(monkeypatch):
    import app.main as main_module
    importlib.reload(main_module)

    # Reset the module-level cache so prior tests can't pre-warm it.
    main_module._ep_cache["n"] = None
    main_module._ep_cache["ts"] = 0.0
    main_module.fm_client.cache_clear()

    calls = {"n": 0}

    class FakeClient:
        def list_endpoints(self):
            calls["n"] += 1
            if calls["n"] == 1:
                raise RuntimeError("databricks transient outage")
            return [{"name": "ep1"}, {"name": "ep2"}]

    monkeypatch.setattr(main_module, "fm_client", lambda: FakeClient())

    client = TestClient(main_module.app)

    # First probe: failure → degraded.
    r1 = client.get("/health")
    assert r1.status_code == 200
    body1 = r1.json()
    assert body1["fm_ok"] is False, f"expected first probe degraded, got {body1}"
    assert body1["status"] == "degraded"

    # Second probe immediately after: Databricks has "recovered" (the fake
    # client returns 2 endpoints on call #2). Buggy code returns the cached
    # failure for the next 60s; correct code retries and returns healthy.
    r2 = client.get("/health")
    assert r2.status_code == 200
    body2 = r2.json()
    assert body2["fm_ok"] is True, (
        f"BUG: /health served stale cached failure after recovery — got {body2}; "
        f"fm_client was called {calls['n']} time(s) (expected 2)"
    )
    assert body2["fm_endpoints"] == 2
    assert calls["n"] == 2, (
        f"BUG: /health did not retry after failure — fm_client called {calls['n']} "
        f"time(s); failure ts was cached and short-circuited the second probe"
    )


# --------------------------------------------------------------------------- #
# BUG B — DEMO_KEY auth matrix across 4 env combinations                      #
# --------------------------------------------------------------------------- #
# app/main.py:117-129 (`require_demo_key`). Verify the full truth table:
#   (1) DEMO_KEY="secret", header matches      → 200
#   (2) DEMO_KEY="secret", header missing      → 401
#   (3) DEMO_KEY unset,    AAROGYANET_DEV off  → 401 (fail closed)
#   (4) DEMO_KEY unset,    AAROGYANET_DEV on   → 200 (explicit dev opt-in)
# Module-level DEMO_KEY/DEV_MODE are read at import time, so every case
# reloads app.main after twiddling env vars.
@pytest.mark.parametrize(
    "demo_key,dev_mode,send_header,header_value,expected_status,case_name",
    [
        ("secret",  None, True,  "secret", 200, "key_set_header_matches"),
        ("secret",  None, False, None,     401, "key_set_header_missing"),
        (None,      None, False, None,     401, "key_unset_dev_off_fail_closed"),
        (None,      "1",  False, None,     200, "key_unset_dev_on_explicit_optin"),
    ],
)
def test_bug_demo_key_auth_matrix_all_four_combinations(
    monkeypatch, demo_key, dev_mode, send_header, header_value,
    expected_status, case_name,
):
    # Wipe both env vars first, then set only the ones this case requires.
    monkeypatch.delenv("DEMO_KEY", raising=False)
    monkeypatch.delenv("AAROGYANET_DEV", raising=False)
    if demo_key is not None:
        monkeypatch.setenv("DEMO_KEY", demo_key)
    if dev_mode is not None:
        monkeypatch.setenv("AAROGYANET_DEV", dev_mode)

    import app.main as main_module
    importlib.reload(main_module)

    # Stub out book_atomic so a successful auth doesn't blow up on missing
    # warehouse/transcript wiring — the only thing under test is the auth gate.
    monkeypatch.setattr(
        main_module, "book_atomic",
        lambda f, p, _: {"transaction_id": "uuid", "status": "COMMITTED",
                         "resources": {"bed": "OK", "ambulance": "OK",
                                       "doctor": "OK", "drug": "OK"},
                         "facility_id": f, "commit_error": None},
    )

    client = TestClient(main_module.app)
    headers = {"X-Demo-Key": header_value} if send_header else {}
    r = client.post(
        "/book",
        json={"facility_id": "5603", "patient_id": "p_matrix"},
        headers=headers,
    )

    assert r.status_code == expected_status, (
        f"case={case_name}: DEMO_KEY={demo_key!r} AAROGYANET_DEV={dev_mode!r} "
        f"send_header={send_header} header={header_value!r} — "
        f"expected {expected_status}, got {r.status_code}: {r.text}"
    )

    # Cleanup: clear DEMO_KEY before next test imports app.main.
    monkeypatch.delenv("DEMO_KEY", raising=False)
    importlib.reload(main_module)
