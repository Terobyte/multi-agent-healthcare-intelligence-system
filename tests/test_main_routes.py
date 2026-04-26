"""Route-level smoke tests using FastAPI's TestClient.

These exercise FastAPI's response_model serialization + the new auth/rate-limit
plumbing. The booking saga itself is covered by tests/test_booking.py.
"""
import os
import importlib

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client_with_key(monkeypatch):
    monkeypatch.setenv("DEMO_KEY", "test-secret")
    # Force re-import so module-level DEMO_KEY pickup uses the env we just set.
    import app.main as main_module
    importlib.reload(main_module)
    yield TestClient(main_module.app), main_module
    importlib.reload(main_module)  # restore for sibling tests


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


def test_book_warehouse_failure_returns_rejected_not_500(client_with_key, monkeypatch):
    """If book_atomic raises, /book must return a structured BookingOutput, not 500."""
    client, main_module = client_with_key

    def boom(*a, **kw):
        raise RuntimeError("warehouse exploded")

    monkeypatch.setattr(main_module, "book_atomic", boom)
    r = client.post("/book", json={"facility_id": "5603", "patient_id": "p3"},
                    headers={"X-Demo-Key": "test-secret"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "REJECTED"
    assert body["reason"] == "warehouse unavailable"
    assert body["transaction_id"] is None
    # Must NOT leak the raw exception text
    assert "warehouse exploded" not in r.text
