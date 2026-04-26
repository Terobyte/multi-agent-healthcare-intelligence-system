"""Mosaic AI Knowledge Assistant — STUB ONLY.

Real KA wiring is deferred per ``SPONSOR_STACK_PLAN.md`` v2 §Drop list:
Mubarak's RAG track may rewire ``triage()`` to query ``mubarak_vs`` directly,
and we don't want two competing retrieval paths colliding mid-hackathon.

The pitch line «Knowledge Assistant on Vector Search» still holds because the
interface here returns the same shape KA's serving endpoint would (``matches``
list with ``text`` + ``score``). When the real wiring lands, only
:meth:`KnowledgeAssistantStub._live_query` flips on; the call sites stay
identical.

Real-mode call (when enabled, NOT in this branch):

    from databricks.sdk import WorkspaceClient
    w = WorkspaceClient()
    res = w.serving_endpoints.query(
        name="aarogyanet_symptom_ka",
        inputs=[{"messages": [{"role": "user", "content": symptom_text}]}],
    )

There is NO ``KnowledgeAssistantClient.query()`` SDK class — that was a
hallucination in plan v1.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from app.sponsor.flags import flags


logger = logging.getLogger(__name__)


_CORPUS_PATH: Path = Path(__file__).parent.parent / "agents" / "symptom_corpus.json"


def _load_corpus() -> list[dict[str, Any]]:
    """Load the symptom corpus.

    Raises ``RuntimeError`` if the corpus file is missing/corrupt/malformed —
    callers can distinguish a broken data source from a successful retrieval
    that simply found no matches. The :class:`KnowledgeAssistantStub` init
    catches this so the demo never hard-crashes at import time, but the
    function itself surfaces the failure honestly.
    """
    try:
        return json.loads(_CORPUS_PATH.read_text())["corpus"]
    except (FileNotFoundError, json.JSONDecodeError, KeyError, OSError) as exc:
        logger.warning("symptom corpus unavailable: %s", exc)
        raise RuntimeError(f"symptom corpus unavailable: {exc}") from exc


def _keyword_match(symptom_text: str, corpus: list[dict[str, Any]], k: int = 5) -> list[dict[str, Any]]:
    """Return up to ``k`` corpus entries whose keywords appear in the input.

    Mirrors the existing keyword fallback in :mod:`app.agents.triage` so the
    stub returns the same kind of result the real KA endpoint would (relevance-
    ranked symptom→specialty mappings).

    Rows whose ``urgency`` cannot be coerced to ``int`` (e.g. legacy "red"
    sentinel values from older corpus versions) are skipped rather than
    propagated — a single malformed row must not crash retrieval.
    """
    text_lower = symptom_text.lower()
    scored: list[tuple[int, int, dict[str, Any]]] = []
    malformed = 0
    inspected = 0
    for entry in corpus:
        inspected += 1
        score = sum(1 for kw in entry.get("keywords", []) if kw.lower() in text_lower)
        if score <= 0:
            continue
        raw_urgency = entry.get("urgency", 0)
        try:
            urgency_int = int(raw_urgency)
        except (TypeError, ValueError):
            logger.debug("skipping corpus row with non-numeric urgency: %r", raw_urgency)
            malformed += 1
            continue
        scored.append((score, urgency_int, entry))
    # bug #113: surface a degraded corpus loudly. If >10% of inspected rows
    # were unparseable, an upstream ETL change has likely broken the source.
    # Without this warning callers see "no matches" — indistinguishable from
    # a legitimate empty result — and the issue ships silently.
    if inspected > 0 and (malformed / inspected) > 0.10:
        logger.warning(
            "knowledge_assistant_corpus_degraded malformed=%d inspected=%d (%.0f%%)",
            malformed, inspected, 100.0 * malformed / inspected,
        )
    scored.sort(key=lambda x: (-x[0], -x[1]))
    return [
        {
            "text": ", ".join(e.get("keywords", [])[:3]),
            "specialty": e.get("specialty", ""),
            "urgency": urgency_int,
            "bed_type": e.get("bed_type", ""),
            "score": float(score),
        }
        for score, urgency_int, e in scored[:k]
    ]


class KnowledgeAssistantStub:
    """KA-shaped retrieval that always uses the local JSON corpus.

    The class is intentionally KA-compatible: same return shape as the real
    serving endpoint would emit, so flipping on the live path is a one-method
    change rather than a refactor.
    """

    def __init__(self) -> None:
        # _load_corpus now raises RuntimeError on a broken source so callers
        # who care can distinguish broken from no-match. The stub itself
        # degrades to an empty corpus so the demo never crashes at import time.
        try:
            self._corpus = _load_corpus()
        except RuntimeError as exc:
            logger.warning("KA stub starting with empty corpus: %s", exc)
            self._corpus = []

    def retrieve(self, symptom_text: str, *, k: int = 5) -> dict[str, Any]:
        if flags.SPONSOR_KA and not flags.SAFE_DEMO:
            # Live path is intentionally not implemented yet — see module
            # docstring. Falling back to the stub keeps demo behavior stable.
            logger.debug("SPONSOR_KA live path not implemented; using stub")
        matches = _keyword_match(symptom_text, self._corpus, k=k)
        return {"matches": matches, "source": "stub"}
