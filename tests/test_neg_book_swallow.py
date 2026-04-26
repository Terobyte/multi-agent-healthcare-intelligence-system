"""Negative test: POST /book must NOT swallow DB exceptions.

Around app/main.py:194-207, the /book handler wraps the entire body in
``try: ... except Exception:`` and returns a synthesized
``BookingOutput(status="REJECTED", reason="warehouse unavailable")`` with
HTTP 200. That makes a real DB outage indistinguishable — to monitoring,
to alerting, and to the client — from a legitimate booking rejection
(facility missing, duplicate active txn, child MERGE failed, etc.).

This test simulates a DB outage by monkey-patching ``book_atomic`` to raise
``RuntimeError("simulated DB outage")``. A correctly-behaving handler
should bubble the failure up as a 5xx so ops sees the outage. The current
handler catches it and returns 200, so this test is RED on master.
"""
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
    import app.main as main_module
    importlib.reload(main_module)
    yield TestClient(main_module.app, raise_server_exceptions=False), main_module
    monkeypatch.delenv("DEMO_KEY", raising=False)
    importlib.reload(main_module)


def test_book_does_not_swallow_db_outage(client_with_key, monkeypatch):
    """A DB outage must surface as 5xx, NOT a 200 with status=REJECTED.

    Returning 200 hides outages from uptime monitoring, masks them in the
    request-success-rate SLO, and prevents the frontend from distinguishing
    "the warehouse is down" from "this booking was legitimately rejected".
    """
    client, main_module = client_with_key

    def simulated_db_outage(*args, **kwargs):
        raise RuntimeError("simulated DB outage")

    # Patch the symbol the /book handler actually calls (imported into app.main).
    monkeypatch.setattr(main_module, "book_atomic", simulated_db_outage)

    r = client.post(
        "/book",
        json={"facility_id": "5603", "patient_id": "p-outage"},
        headers={"X-Demo-Key": "test-secret"},
    )

    # The handler currently catches Exception and returns 200/REJECTED.
    # That is the bug. A DB outage must be a 5xx so monitoring can see it.
    assert r.status_code >= 500, (
        f"DB outage was swallowed: got {r.status_code} body={r.text!r}. "
        "POST /book must not catch all exceptions and return a synthesized "
        "REJECTED — that hides infrastructure failures from monitoring."
    )
