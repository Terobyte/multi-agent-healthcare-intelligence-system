"""System-boundary contracts.

Sweep #2 of bugs.md showed the same shape repeated across 10 critical findings:
the codebase fixes individual leaks but never names the *boundary* being
violated.  This module defines the small set of boundary helpers every leg of
the saga / SSE / sponsor stack should route through, so future code can opt
into the contract instead of hand-rolling timeouts and ownership checks.

Three boundaries:

1. ``with_io_deadline`` — every external call has an upper-bound wall-clock
   deadline. Without this, a hung Databricks warehouse holds the FastAPI
   worker for ``socket_timeout`` seconds (45s in db.py) plus N retries plus
   N more for the next chained call.
2. ``bounded_put`` — async producers must not block forever on a slow
   consumer; if the queue is full past ``deadline_s`` the put is dropped (or
   the producer aborts), surfacing back-pressure instead of OOMing the worker.
3. ``as_owner`` — read a tenant-scoped resource only after verifying that the
   request principal owns it.  Genie conversations, transactions, and feedback
   rows all need this; today they read by id with no ownership check.

These are *light* helpers — Python decorators / async functions, not a
framework. The goal is to make the boundary visible at every call site so a
reviewer can grep for ``with_io_deadline`` and know the call has a deadline.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Awaitable, Callable, Optional, TypeVar

logger = logging.getLogger("boundaries")

T = TypeVar("T")


class BoundaryViolation(RuntimeError):
    """Raised when a boundary contract is violated (timeout, ownership, etc.).

    Distinct from a generic Exception so the global 500 handler in main.py can
    map it to a structured 5xx with a meaningful detail and trace_id.
    """


async def with_io_deadline(
    coro: Awaitable[T],
    *,
    deadline_s: float,
    op: str,
) -> T:
    """Wrap an awaitable with a wall-clock deadline.

    ``coro`` is typically ``asyncio.to_thread(warehouse_query, ...)`` or an
    httpx call. ``deadline_s`` should be tighter than the underlying socket
    timeout — the goal is a *route-level* SLA (e.g. 8s for /book) so the user
    sees a 503 rather than waiting on the back-end retry budget.
    """
    try:
        return await asyncio.wait_for(coro, timeout=deadline_s)
    except asyncio.TimeoutError as exc:
        logger.warning("io_deadline_exceeded op=%s deadline=%.1fs", op, deadline_s)
        raise BoundaryViolation(
            f"upstream {op} exceeded {deadline_s:.1f}s deadline"
        ) from exc


async def bounded_put(
    queue: asyncio.Queue,
    item: Any,
    *,
    deadline_s: float = 5.0,
    op: str = "queue_put",
) -> bool:
    """Put on a bounded queue with a deadline.

    Returns ``True`` on success, ``False`` if the queue stayed full for
    ``deadline_s`` and the item was dropped. Use ``False`` to either abort the
    producer or downgrade to a lossy "best-effort" mode (heartbeats can be
    dropped; payload events should usually abort).
    """
    try:
        await asyncio.wait_for(queue.put(item), timeout=deadline_s)
        return True
    except asyncio.TimeoutError:
        logger.warning("bounded_put_dropped op=%s deadline=%.1fs", op, deadline_s)
        return False


def as_owner(
    *,
    expected_owner: Optional[str],
    resource_owner: Optional[str],
    resource_kind: str,
) -> None:
    """Raise BoundaryViolation if the principal doesn't own the resource.

    ``expected_owner`` is whatever stable identity the request carries
    (session id, demo key derivative, X-Demo-Key hash). ``resource_owner`` is
    the value persisted with the resource (e.g. the conversation owner stored
    by GenieClient). Either being None is treated as a violation — anonymous
    cross-access is exactly the bug we want to block.
    """
    if not expected_owner or not resource_owner:
        raise BoundaryViolation(
            f"{resource_kind}: ownership check requires both principal and "
            "resource owner to be set; refusing anonymous access"
        )
    if expected_owner != resource_owner:
        raise BoundaryViolation(
            f"{resource_kind}: principal does not own the requested resource"
        )
