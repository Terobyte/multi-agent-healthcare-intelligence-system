"""Failing test for SSE error-path contract.

When the producer inside `/sse` raises mid-loop, the handler emits an
`event: error` frame and then returns without ever emitting `event: done`.
A correctly-written EventSource client on the frontend treats `done` as the
ONLY terminal frame — without it, the connection is observed as still
streaming and the reasoning panel stays stuck forever.

Contract: every SSE response from `/sse` MUST end with an `event: done`
frame, even on the exception path. This test FAILS today against
app/main.py:262-268 (producer) — the `except` branch emits `error` and
falls through to `finally: queue.put(DONE)` which closes the generator
WITHOUT sending a `done` frame.

See test_known_bugs_sse.py for the fixture / reload pattern.
"""
import asyncio
import importlib
import os

from fastapi.testclient import TestClient


def _fresh_main():
    if "DEMO_KEY" in os.environ:
        del os.environ["DEMO_KEY"]
    import app.main as main_module
    importlib.reload(main_module)
    return main_module


def _parse_sse_events(body: str) -> list[str]:
    """Return ordered list of `event:` field values from an SSE body."""
    events: list[str] = []
    for frame in body.split("\n\n"):
        for line in frame.splitlines():
            if line.startswith("event:"):
                events.append(line.split(":", 1)[1].strip())
                break
    return events


def test_sse_must_emit_done_even_after_error_frame(monkeypatch):
    """If the producer raises, `event: error` MUST be followed by `event: done`.

    Without a terminal `done` frame the frontend EventSource has no signal to
    stop the spinner and the reasoning panel hangs in "streaming" state. We
    inject a synthetic failure by monkey-patching `_evt` (called for every
    agent step in the producer loop) to raise on the second invocation —
    after some output, before completion. The `except` in the producer then
    fires, emits `event: error`, and the generator exits via `finally`
    WITHOUT a `done` frame. Test asserts `done` appears AFTER `error` in
    the event sequence — RED today, GREEN once main.py emits `done` in the
    except branch as well.
    """
    main_module = _fresh_main()

    real_evt = main_module._evt
    call_count = {"n": 0}

    def boom_evt(agent: str, token: str, trace_id: str) -> str:
        call_count["n"] += 1
        # Let the first event through so the stream looks alive, then raise
        # to drive the producer into its `except Exception` branch.
        if call_count["n"] >= 2:
            raise RuntimeError("synthetic agent failure for SSE error-path test")
        return real_evt(agent, token, trace_id)

    monkeypatch.setattr(main_module, "_evt", boom_evt)

    # Tighten the stream so the test runs in <1s — irrelevant to the bug,
    # just keeps the harness fast.
    real_sleep = asyncio.sleep

    async def fast_sleep(_secs):
        await real_sleep(0.01)

    monkeypatch.setattr(main_module.asyncio, "sleep", fast_sleep)

    client = TestClient(main_module.app)
    with client.stream("GET", "/sse?session_id=err") as r:
        body = b"".join(r.iter_bytes()).decode()

    events = _parse_sse_events(body)

    assert "error" in events, (
        f"precondition: producer should have raised and emitted event: error. "
        f"Got events={events}. Body:\n{body[:600]}"
    )

    error_idx = events.index("error")
    tail = events[error_idx + 1:]
    assert "done" in tail, (
        f"contract: every /sse response MUST terminate with `event: done`, "
        f"even after `event: error`. Without it the frontend EventSource has "
        f"no terminal signal and the reasoning panel stays stuck in "
        f"'streaming' forever. Got events={events}. Body:\n{body[:800]}"
    )
