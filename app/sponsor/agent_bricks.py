"""Mosaic AI Agent Framework wrapper around the existing ``triage()`` agent.

This module conforms to the Databricks Agent Framework (Mosaic AI Agent Bricks)
spec by subclassing ``mlflow.pyfunc.ResponsesAgent`` — the current shape that
log_model + AI Playground + Agent Evaluation expect as of MLflow 3.x. The
legacy ``PythonModel`` shape is NOT used because it doesn't auto-wire those
sponsor surfaces.

The wrapper does not replace ``/triage``. It exposes a parallel sponsor route
``/sponsor/triage`` that returns the same :class:`TriageOutput` payload but
gives us the «deployed via Agent Framework» pitch line.

Stub-safe: if ``mlflow``/``databricks-agents`` is not installed, the module
still imports — ``BRICKS_AVAILABLE`` flips to False and the route returns a
canned response so the demo doesn't crash on a fresh laptop.
"""
from __future__ import annotations

import logging
from typing import Any

from app.agents.triage import triage as _triage_function
from app.schemas import TriageOutput


logger = logging.getLogger(__name__)


try:
    from mlflow.pyfunc import ResponsesAgent
    from mlflow.types.agent import ResponsesAgentRequest, ResponsesAgentResponse

    BRICKS_AVAILABLE = True
except Exception:  # pragma: no cover — fallback path used on hosts without mlflow 3.x
    ResponsesAgent = object  # type: ignore[assignment,misc]
    ResponsesAgentRequest = Any  # type: ignore[assignment,misc]
    ResponsesAgentResponse = Any  # type: ignore[assignment,misc]
    BRICKS_AVAILABLE = False


def _extract_user_text(request: Any) -> str:
    """Pull the most recent user message text out of a ResponsesAgent request.

    The Responses API shape allows multi-turn input; we only care about the
    last user turn. Defensive against missing fields so a malformed call
    doesn't crash mid-demo.
    """
    items = getattr(request, "input", None) or []
    for item in reversed(items):
        content = getattr(item, "content", None)
        if isinstance(content, str) and content:
            return content
        if isinstance(content, list):
            for part in reversed(content):
                text = getattr(part, "text", None) or (
                    part.get("text") if isinstance(part, dict) else None
                )
                if text:
                    return str(text)
    return ""


class TriageResponsesAgent(ResponsesAgent):  # type: ignore[misc]
    """ResponsesAgent that delegates to the existing ``triage()`` function.

    Why a thin wrapper rather than a fresh agent: ``triage()`` already
    encapsulates the Llama 3.3 70B call, the keyword fallback, and the
    sanitization pipeline (see ``app/agents/triage.py``). Re-implementing
    that logic inside the wrapper would diverge from the production
    ``/triage`` route's behaviour and break the trust calibration story.
    """

    def predict(self, request: Any) -> Any:  # noqa: D401
        symptoms = _extract_user_text(request)
        # Optional language hint passed through ``custom_inputs`` if the caller
        # set it. Default to English.
        language = "en"
        custom = getattr(request, "custom_inputs", None) or {}
        if isinstance(custom, dict):
            lang_in = custom.get("language")
            if isinstance(lang_in, str) and lang_in:
                language = lang_in

        result: TriageOutput = _triage_function(symptoms, language)
        payload = result.model_dump_json()

        return ResponsesAgentResponse(
            output=[
                {
                    "type": "message",
                    "role": "assistant",
                    "content": [{"type": "output_text", "text": payload}],
                }
            ]
        )


def run_triage(symptoms: str, language: str = "en") -> TriageOutput:
    """Functional path used by the FastAPI route.

    Always calls ``triage()`` directly — going through ``predict`` would force
    us to construct a ResponsesAgentRequest just to deconstruct it again. The
    Agent Framework ceremony lives in :class:`TriageResponsesAgent` for the
    log_model script; the route just calls the same underlying function so the
    sponsor path and Mubarak's path stay observably identical.

    Defensive guarantees:
    - blank/whitespace-only symptoms raise ``ValueError`` before the LLM call
      so we never spend a Databricks token on noise
    - any exception from the underlying triage function is converted to a
      safe ``TriageOutput`` fallback so the sponsor route never returns 500
      mid-demo
    """
    if symptoms is None or not symptoms.strip():
        raise ValueError("symptoms is blank/empty; required input")

    try:
        return _triage_function(symptoms, language)
    except Exception as exc:  # broad: triage ↔ Llama outage → safe fallback
        logger.warning(
            "sponsor triage failed (%s: %s); returning safe fallback",
            type(exc).__name__,
            exc,
            exc_info=True,
        )
        return TriageOutput(
            specialty="general medicine",
            urgency=1,
            confidence=0.0,
            required_bed_type="general",
            fast_path=False,
            red_flag_match=[],
            reasoning="error fallback: upstream triage unavailable",
        )
