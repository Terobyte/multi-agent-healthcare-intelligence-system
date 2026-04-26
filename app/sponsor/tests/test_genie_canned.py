"""Tests for the Genie wrapper — canned mode and fallback behavior.

No network. No Databricks creds. The live path is exercised by an integration
test under ``@pytest.mark.live`` (not run in CI).
"""
from __future__ import annotations

import os

import pytest


@pytest.fixture(autouse=True)
def _reset_env(monkeypatch):
    """Force canned mode by default; tests opt into live behavior explicitly."""
    monkeypatch.delenv("SPONSOR_GENIE_LIVE", raising=False)
    monkeypatch.delenv("SAFE_DEMO", raising=False)


def test_canned_mode_is_default(monkeypatch):
    from app.sponsor.genie import GenieClient

    g = GenieClient()
    res = g.ask(conversation_id=None, query="show me ICU beds available")

    assert res["source"] == "canned"
    assert "ICU" in res["sql"] or "icu" in res["sql"].lower()
    assert len(res["rows"]) > 0
    # Field-name discipline: facility_id, not hospital_id.
    assert "facility_id" in res["sql"]


def test_canned_picks_best_keyword_match():
    from app.sponsor.genie import GenieClient

    g = GenieClient()
    res = g.ask(conversation_id=None, query="cardiac specialty")

    # Cardiology entry should win because keyword 'cardiac' matches.
    assert "cardiology" in res["sql"].lower()


def test_canned_returns_empty_shape_when_no_keyword_overlap():
    from app.sponsor.genie import GenieClient

    g = GenieClient()
    res = g.ask(conversation_id=None, query="random unrelated nonsense")

    # Even with zero matches, shape is well-formed (no crash).
    assert "sql" in res
    assert "rows" in res
    assert "explanation" in res
    assert res["source"] == "canned"


def test_safe_demo_overrides_live_flag(monkeypatch):
    monkeypatch.setenv("SPONSOR_GENIE_LIVE", "true")
    monkeypatch.setenv("SAFE_DEMO", "true")

    from app.sponsor.genie import GenieClient

    g = GenieClient()
    res = g.ask(conversation_id=None, query="ICU beds")

    # SAFE_DEMO wins over SPONSOR_GENIE_LIVE — must not attempt a live call.
    assert res["source"] == "canned"


def test_live_falls_back_to_canned_when_space_id_missing(monkeypatch):
    monkeypatch.setenv("SPONSOR_GENIE_LIVE", "true")
    monkeypatch.delenv("DATABRICKS_GENIE_SPACE_ID", raising=False)

    from app.sponsor.genie import GenieClient

    g = GenieClient()
    res = g.ask(conversation_id=None, query="ICU beds")

    assert res["source"] == "canned"


def test_conversation_id_preserved_in_canned_mode():
    from app.sponsor.genie import GenieClient

    g = GenieClient()
    res = g.ask(conversation_id="demo-conv-7", query="trust >= 0.8")

    assert res["conversation_id"] == "demo-conv-7"
