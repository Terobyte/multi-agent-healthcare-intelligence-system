"""Route-level smoke tests using FastAPI's TestClient.

These exercise FastAPI's response_model serialization + the new auth/rate-limit
plumbing. The booking saga itself is covered by tests/test_booking.py.
"""
import os
import importlib

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def _allow_dev_salt(monkeypatch):
    monkeypatch.setenv("AAROGYANET_DEV", "1")
    monkeypatch.delenv("PII_SALT", raising=False)


@pytest.fixture
def client_with_key(monkeypatch):
    monkeypatch.setenv("DEMO_KEY", "test-secret")
    # Force re-import so module-level DEMO_KEY pickup uses the env we just set.
    import app.main as main_module
    importlib.reload(main_module)
    yield TestClient(main_module.app), main_module
    # Unset DEMO_KEY BEFORE the cleanup reload so the module's DEMO_KEY binding
    # doesn't keep "test-secret" alive for sibling tests that import app.main.
    # monkeypatch.undo() unwinds AFTER fixture teardown — too late.
    monkeypatch.delenv("DEMO_KEY", raising=False)
    importlib.reload(main_module)


def test_book_rejects_without_demo_key(client_with_key, monkeypatch):
    client, main_module = client_with_key
    monkeypatch.setattr(
        main_module, "book_atomic",
        lambda f, p, _: {"transaction_id": "uuid", "status": "COMMITTED",
                         "resources": {"bed": "OK"}, "facility_id": f, "commit_error": None},
    )
    r = client.post("/book", json={"facility_id": "5603", "patient_id": "p1"})
    assert r.status_code == 401


def test_book_accepts_with_demo_key(client_with_key, monkeypatch):
    client, main_module = client_with_key
    monkeypatch.setattr(
        main_module, "book_atomic",
        lambda f, p, _: {"transaction_id": "uuid-1", "status": "COMMITTED",
                         "resources": {"bed": "OK", "ambulance": "OK", "doctor": "OK", "drug": "OK"},
                         "facility_id": f, "commit_error": None},
    )
    r = client.post("/book", json={"facility_id": "5603", "patient_id": "p2"},
                    headers={"X-Demo-Key": "test-secret"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "COMMITTED"
    assert body["transaction_id"] == "uuid-1"
    assert body["commit_error"] is None


def test_sse_demo_replays_transcript():
    # No demo key needed — it's a read-only demo endpoint.
    if "DEMO_KEY" in os.environ:
        del os.environ["DEMO_KEY"]
    import app.main as main_module
    importlib.reload(main_module)
    client = TestClient(main_module.app)
    with client.stream("GET", "/sse_demo?session_id=test") as r:
        assert r.status_code == 200
        body = b"".join(r.iter_bytes())
    text = body.decode()
    assert "event: triage" in text
    assert "event: done" in text


def test_sse_demo_synthesizes_done_when_transcript_lacks_one(monkeypatch, tmp_path):
    """Malformed transcript (no done frame) must NOT silently leave the panel hanging."""
    bad = tmp_path / "bad.sse"
    bad.write_text("event: triage\ndata: {\"agent\":\"triage\",\"token\":\"x\"}\n\n")
    if "DEMO_KEY" in os.environ:
        del os.environ["DEMO_KEY"]
    import app.main as main_module
    importlib.reload(main_module)
    monkeypatch.setattr(main_module, "_DEMO_TRANSCRIPT", bad)
    client = TestClient(main_module.app)
    with client.stream("GET", "/sse_demo?session_id=t") as r:
        body = b"".join(r.iter_bytes()).decode()
    assert "event: triage" in body
    assert "event: done" in body
    assert "demo_transcript_invalid" in body


def test_book_warehouse_failure_returns_500_without_token_leak(client_with_key, monkeypatch):
    """If book_atomic raises (DB outage), /book must surface as 5xx so monitoring
    sees the outage. The raw exception text must NOT leak into the response.

    Updated contract (was: 200/REJECTED). Returning 200 on infra failures hid
    outages from uptime monitoring and the request-success SLO. The new
    bubble-up + scrubbed-500 path keeps token-leak prevention while making
    outages visible (see test_neg_book_swallow + test_bug20).
    """
    _, main_module = client_with_key

    def boom(*a, **kw):
        raise RuntimeError("warehouse exploded")

    monkeypatch.setattr(main_module, "book_atomic", boom)
    bubble_client = TestClient(main_module.app, raise_server_exceptions=False)
    r = bubble_client.post("/book", json={"facility_id": "5603", "patient_id": "p3"},
                           headers={"X-Demo-Key": "test-secret"})
    assert r.status_code == 500, r.text
    # Must NOT leak the raw exception text
    assert "warehouse exploded" not in r.text
