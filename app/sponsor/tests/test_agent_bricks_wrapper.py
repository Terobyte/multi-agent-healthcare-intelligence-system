"""Unit tests for the Agent Bricks wrapper.

These tests do NOT require a live Databricks workspace, MLflow tracking
server, or network. They verify that:

1. The wrapper module imports even when mlflow 3.x isn't installed.
2. ``run_triage`` returns a well-formed ``TriageOutput`` (offline keyword path).
3. ``_extract_user_text`` is robust to malformed Responses-API payloads.
"""
from __future__ import annotations

import os

import pytest

from app.schemas import TriageOutput


# Force the offline keyword fallback so triage() doesn't try to hit Databricks.
os.environ.setdefault("VS_ENDPOINT", "")


def test_module_imports_without_mlflow_3():
    # Import alone should never raise — even if mlflow.pyfunc.ResponsesAgent
    # isn't available, the module flips to BRICKS_AVAILABLE=False instead.
    from app.sponsor import agent_bricks

    assert hasattr(agent_bricks, "BRICKS_AVAILABLE")
    assert hasattr(agent_bricks, "TriageResponsesAgent")
    assert hasattr(agent_bricks, "run_triage")


def test_run_triage_returns_well_formed_output():
    from app.sponsor.agent_bricks import run_triage

    result = run_triage("chest pain since morning", language="en")

    assert isinstance(result, TriageOutput)
    assert 1 <= result.urgency <= 5
    assert 0.0 <= result.confidence <= 1.0
    assert result.required_bed_type in {
        "icu", "hdu", "general", "pediatric", "maternity", "isolation"
    }


def test_extract_user_text_handles_string_content():
    from app.sponsor.agent_bricks import _extract_user_text

    class _FakeItem:
        content = "headache"

    class _FakeRequest:
        input = [_FakeItem()]

    assert _extract_user_text(_FakeRequest()) == "headache"


def test_extract_user_text_handles_list_content_dict_parts():
    from app.sponsor.agent_bricks import _extract_user_text

    class _FakeItem:
        content = [{"type": "input_text", "text": "fever"}]

    class _FakeRequest:
        input = [_FakeItem()]

    assert _extract_user_text(_FakeRequest()) == "fever"


def test_extract_user_text_returns_empty_on_malformed_input():
    from app.sponsor.agent_bricks import _extract_user_text

    class _FakeRequest:
        input = []

    assert _extract_user_text(_FakeRequest()) == ""
