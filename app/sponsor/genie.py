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
import threading
from datetime import timedelta
from pathlib import Path
from typing import Any

from app.boundaries import as_owner
from app.sponsor.flags import flags


logger = logging.getLogger(__name__)


_CANNED_PATH: Path = Path(__file__).parent / "_demo" / "demo_genie_canned.json"


_WORKSPACE_INIT_LOCK: threading.Lock = threading.Lock()


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
        self._workspace_lock: threading.Lock = threading.Lock()
        # critical-bug #8: in-process owner ledger. A real prod build would
        # persist this in the warehouse so it survives replicas; for the
        # hackathon a per-instance dict closes the most obvious cross-tenant
        # read on a single Railway replica.
        self._conversation_owners: dict[str, str] = {}

    def _workspace(self) -> Any:
        # Lazy-init under a lock — concurrent live requests must not race to
        # create multiple WorkspaceClient instances and burn parallel auth tokens.
        # bug #101: pass an explicit http timeout so an unresponsive auth
        # endpoint cannot pin the worker (and the lock) forever. The SDK reads
        # ``http_timeout_seconds`` directly off WorkspaceClient kwargs.
        lock = self._workspace_lock
        with lock:
            if self._w is None:
                from databricks.sdk import WorkspaceClient

                self._w = WorkspaceClient(http_timeout_seconds=15)
        return self._w

    def ask(
        self,
        conversation_id: str | None,
        query: str,
        *,
        owner: str | None = None,
    ) -> dict[str, Any]:
        """Ask Genie a natural-language question.

        critical-bug #8 (tenant boundary): ``owner`` is a stable identifier
        for the calling principal (X-Demo-Key hash, session id). When the
        caller resumes a conversation, we record the owner the first time
        and refuse cross-tenant resume on subsequent calls so consumer A
        cannot read consumer B's chat history through Genie's
        conversation_id surface.

        Returns ``{"conversation_id": str | None, "sql": str, "rows": list,
        "explanation": str, "source": "canned" | "live"}``.
        """
        # Ownership gate: if a conversation_id is provided, it MUST match the
        # owner we recorded when the conversation was opened. Anonymous
        # access (owner=None) is treated as a violation when resuming.
        if conversation_id:
            recorded = self._conversation_owners.get(conversation_id)
            if recorded is not None:
                as_owner(
                    expected_owner=owner,
                    resource_owner=recorded,
                    resource_kind="genie_conversation",
                )

        if flags.SAFE_DEMO or not flags.SPONSOR_GENIE_LIVE:
            result = self._canned_response(conversation_id, query)
        elif not self._space_id:
            logger.warning("SPONSOR_GENIE_LIVE is true but DATABRICKS_GENIE_SPACE_ID is unset; using canned")
            result = self._canned_response(conversation_id, query)
        else:
            try:
                result = self._live_response(conversation_id, query)
            except Exception as exc:  # broad: any SDK error → canned fallback
                logger.warning(
                    "genie live call failed (%s: %s); falling back to canned",
                    type(exc).__name__,
                    exc,
                    exc_info=True,
                )
                result = self._canned_response(conversation_id, query)

        # Record ownership on the resulting conversation_id so the next
        # resume can be gated. Only record when an owner was actually
        # supplied — anonymous opens don't claim ownership.
        out_conv_id = result.get("conversation_id")
        if out_conv_id and owner and out_conv_id not in self._conversation_owners:
            self._conversation_owners[out_conv_id] = owner
        return result

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
        if not conversation_id:
            res = w.genie.start_conversation_and_wait(
                space_id=self._space_id,
                content=query,
                timeout=timedelta(seconds=30),
            )
            conv_id = res.conversation_id
            message_id = getattr(res, "message_id", None) or getattr(res, "id", None)
        else:
            res = w.genie.create_message_and_wait(
                space_id=self._space_id,
                conversation_id=conversation_id,
                content=query,
                timeout=timedelta(seconds=30),
            )
            conv_id = conversation_id
            message_id = getattr(res, "id", None) or getattr(res, "message_id", None)

        sql = ""
        rows: list[Any] = []
        columns: list[str] = []
        explanation = ""

        for att in (getattr(res, "attachments", None) or []):
            attachment_id = getattr(att, "attachment_id", None)

            text_obj = getattr(att, "text", None)
            if text_obj is not None:
                content_attr = getattr(text_obj, "content", None)
                if content_attr and not explanation:
                    explanation = content_attr

            query_obj = getattr(att, "query", None)
            if query_obj is not None:
                stmt = getattr(query_obj, "statement", "") or ""
                if stmt:
                    sql = stmt

                # Genie spaces store the result under the attachment, not the
                # message — get_message_query_result returns empty for these
                # rooms, so use the attachment-scoped endpoint instead.
                if attachment_id:
                    try:
                        result = w.genie.get_message_attachment_query_result(
                            space_id=self._space_id,
                            conversation_id=conv_id,
                            message_id=str(message_id),
                            attachment_id=attachment_id,
                        )
                    except Exception as exc:  # pragma: no cover — best-effort enrichment
                        logger.warning(
                            "genie attachment_query_result failed (%s); text-only response",
                            type(exc).__name__,
                        )
                        result = None

                    stmt_resp = getattr(result, "statement_response", None) if result else None
                    if stmt_resp is not None:
                        result_obj = getattr(stmt_resp, "result", None)
                        if result_obj is not None:
                            rows = getattr(result_obj, "data_array", None) or []
                        manifest = getattr(stmt_resp, "manifest", None)
                        schema = getattr(manifest, "schema", None) if manifest else None
                        if schema is not None:
                            columns = [c.name for c in (schema.columns or [])]

        return {
            "conversation_id": conv_id,
            "sql": sql,
            "columns": columns,
            "rows": rows,
            "explanation": explanation,
            "source": "live",
        }
