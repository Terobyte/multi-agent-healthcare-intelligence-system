"""Databricks Genie wrapper — natural-language → SQL on ``gold_trust_final``.

Default mode is canned: returns a hand-curated entry from
``_demo/demo_genie_canned.json`` chosen by keyword overlap with the query. The
canned mode is deterministic and demo-safe.

Live mode (``SPONSOR_GENIE_LIVE=1``) hits ``WorkspaceClient().genie`` with the
correct SDK methods:

- :meth:`databricks.sdk.service.dashboards.GenieAPI.start_conversation_and_wait`
- :meth:`databricks.sdk.service.dashboards.GenieAPI.create_message_and_wait`
- :meth:`databricks.sdk.service.dashboards.GenieAPI.get_message_query_result`

Any exception in live mode falls back to the canned response so a 5xx mid-demo
never reaches the user.
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

from app.sponsor.flags import flags


logger = logging.getLogger(__name__)


_CANNED_PATH: Path = Path(__file__).parent / "_demo" / "demo_genie_canned.json"


def _load_canned() -> list[dict[str, Any]]:
    try:
        return json.loads(_CANNED_PATH.read_text())["queries"]
    except (FileNotFoundError, json.JSONDecodeError, KeyError) as exc:
        logger.warning("genie canned file unavailable: %s", exc)
        return []


def _pick_canned(query: str, canned: list[dict[str, Any]]) -> dict[str, Any]:
    """Pick the canned entry whose ``match_keywords`` best overlap the query."""
    q_lower = query.lower()
    best: tuple[int, dict[str, Any]] | None = None
    for entry in canned:
        keywords = entry.get("match_keywords", []) or []
        score = sum(1 for kw in keywords if kw.lower() in q_lower)
        if best is None or score > best[0]:
            best = (score, entry)
    if best is None:
        # No canned entries — return an empty-but-valid shape so the caller
        # never has to special-case an absent fallback.
        return {"sql": "", "rows": [], "explanation": ""}
    return best[1]


class GenieClient:
    """Thin wrapper over ``WorkspaceClient().genie`` with a canned fallback.

    The class is cheap to construct — the ``WorkspaceClient`` is only created
    when a live call is actually made, so import-time side effects are zero
    even on hosts without Databricks creds.
    """

    def __init__(self) -> None:
        self._space_id = os.getenv("DATABRICKS_GENIE_SPACE_ID", "")
        self._canned = _load_canned()
        self._w: Any = None

    def _workspace(self) -> Any:
        if self._w is None:
            from databricks.sdk import WorkspaceClient

            self._w = WorkspaceClient()
        return self._w

    def ask(self, conversation_id: str | None, query: str) -> dict[str, Any]:
        """Ask Genie a natural-language question.

        Returns ``{"conversation_id": str | None, "sql": str, "rows": list,
        "explanation": str, "source": "canned" | "live"}``.
        """
        if flags.SAFE_DEMO or not flags.SPONSOR_GENIE_LIVE:
            return self._canned_response(conversation_id, query)

        if not self._space_id:
            logger.warning("SPONSOR_GENIE_LIVE is true but DATABRICKS_GENIE_SPACE_ID is unset; using canned")
            return self._canned_response(conversation_id, query)

        try:
            return self._live_response(conversation_id, query)
        except Exception as exc:  # broad: any SDK error → canned fallback
            logger.warning("genie live call failed (%s); falling back to canned", type(exc).__name__)
            return self._canned_response(conversation_id, query)

    def _canned_response(self, conversation_id: str | None, query: str) -> dict[str, Any]:
        entry = _pick_canned(query, self._canned)
        return {
            "conversation_id": conversation_id or "demo-canned",
            "sql": entry.get("sql", ""),
            "rows": entry.get("rows", []),
            "explanation": entry.get("explanation", ""),
            "source": "canned",
        }

    def _live_response(self, conversation_id: str | None, query: str) -> dict[str, Any]:
        w = self._workspace()
        if conversation_id is None:
            res = w.genie.start_conversation_and_wait(
                space_id=self._space_id, content=query
            )
            conv_id = res.conversation_id
            message_id = res.message_id if hasattr(res, "message_id") else res.id
        else:
            res = w.genie.create_message_and_wait(
                space_id=self._space_id,
                conversation_id=conversation_id,
                content=query,
            )
            conv_id = conversation_id
            message_id = res.id if hasattr(res, "id") else res.message_id

        sql = ""
        rows: list[Any] = []
        explanation = ""

        for att in (getattr(res, "attachments", None) or []):
            text_obj = getattr(att, "text", None)
            if text_obj is not None:
                content_attr = getattr(text_obj, "content", None)
                if content_attr:
                    explanation = content_attr
            query_obj = getattr(att, "query", None)
            if query_obj is not None:
                stmt = getattr(query_obj, "statement", "") or ""
                if stmt:
                    sql = stmt
                    result = w.genie.get_message_query_result(
                        space_id=self._space_id,
                        conversation_id=conv_id,
                        message_id=message_id,
                    )
                    stmt_resp = getattr(result, "statement_response", None)
                    if stmt_resp is not None:
                        result_obj = getattr(stmt_resp, "result", None)
                        if result_obj is not None:
                            rows = getattr(result_obj, "data_array", None) or []

        return {
            "conversation_id": conv_id,
            "sql": sql,
            "rows": rows,
            "explanation": explanation,
            "source": "live",
        }
