"""Tests for the Knowledge Assistant stub."""
from __future__ import annotations

import pytest


def test_stub_returns_matches_for_known_symptom():
    from app.sponsor.knowledge_assistant import KnowledgeAssistantStub

    ka = KnowledgeAssistantStub()
    res = ka.retrieve("chest pain since this morning")

    assert res["source"] == "stub"
    assert len(res["matches"]) > 0
    assert res["matches"][0]["specialty"] == "cardiology"
    # Highest-urgency cardiology match should be ranked first when multiple
    # cardiology keywords match.
    assert res["matches"][0]["urgency"] >= 4


def test_stub_returns_empty_matches_for_unknown_symptom():
    from app.sponsor.knowledge_assistant import KnowledgeAssistantStub

    ka = KnowledgeAssistantStub()
    res = ka.retrieve("zzz unrelated nonsense xyz")

    # Empty-but-valid shape — never None, never KeyError.
    assert res["matches"] == []
    assert res["source"] == "stub"


def test_stub_respects_k_limit():
    from app.sponsor.knowledge_assistant import KnowledgeAssistantStub

    ka = KnowledgeAssistantStub()
    res = ka.retrieve("pain", k=2)

    assert len(res["matches"]) <= 2


def test_stub_returns_same_shape_as_real_ka_would():
    from app.sponsor.knowledge_assistant import KnowledgeAssistantStub

    ka = KnowledgeAssistantStub()
    res = ka.retrieve("fever and cough")

    for match in res["matches"]:
        assert "text" in match
        assert "score" in match
        # KA-compatible extras we use downstream.
        assert "specialty" in match
        assert "urgency" in match


def test_stub_stays_stub_when_live_flag_set(monkeypatch):
    monkeypatch.setenv("SPONSOR_KA", "true")

    from app.sponsor.knowledge_assistant import KnowledgeAssistantStub

    ka = KnowledgeAssistantStub()
    res = ka.retrieve("chest pain")

    # Real wiring is deferred — flag toggling must not break the demo.
    assert res["source"] == "stub"
