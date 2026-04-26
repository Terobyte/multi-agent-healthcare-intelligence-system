"""Failing tests for known SSE + config bugs.

Each test FAILS on current code. Committing these locks in the regression so
when someone fixes the bug, the test flips green.

See bugs.md for triage. Bugs covered: #5, #8, #13, #14.
"""
import asyncio
import importlib
import json
import os

import httpx
import pytest
from fastapi.testclient import TestClient


def _fresh_main():
    if "DEMO_KEY" in os.environ:
        del os.environ["DEMO_KEY"]
    import app.main as main_module
    importlib.reload(main_module)
    return main_module


# BUG #5 — SSE heartbeat doesn't actually fire every 15s
# The check `if time.time() - last_ping > 15` is INSIDE the agent loop. With
# placeholder cadence (5 agents × 0.2s ≈ 1s total), the heartbeat never fires.
# Render/Cloudflare idle-close streaming connections after 30-60s of silence.
# Real fix: parallel asyncio.create_task pinging on wall-clock interval.
def test_sse_heartbeat_must_fire_within_15s_when_agent_step_long(monkeypatch):
    main_module = _fresh_main()
    # Make a single agent take >16s by stretching the placeholder sleep.
    monkeypatch.setattr(main_module, "AGENT_ORDER", ["triage"])
    real_sleep = asyncio.sleep

    async def long_sleep(_secs):
        await real_sleep(0.01)  # don't actually wait — fake time

    # Patch time.time to jump 16s mid-loop so the in-loop check WOULD trip if
    # the loop ever reached it. The bug is that the loop completes too fast
    # (only one iteration when AGENT_ORDER is single-element) so the inter-tick
    # check fires AFTER the only `done` step.
    times = iter([1000.0, 1000.0, 1018.0, 1018.0, 1018.0])
    monkeypatch.setattr(main_module.time, "time", lambda: next(times, 1018.0))
    monkeypatch.setattr(main_module.asyncio, "sleep", long_sleep)

    client = TestClient(main_module.app)
    with client.stream("GET", "/sse?session_id=t") as r:
        body = b"".join(r.iter_bytes()).decode()

    ping_count = body.count("event: ping")
    assert ping_count >= 2, (
        f"need ≥2 ping frames (initial + ≥1 mid-stream after 15s) "
        f"to keep the connection alive through proxy idle-close. Got {ping_count}. "
        f"Body:\n{body[:600]}"
    )


# BUG #8 — SSE done event payload doesn't match Block 33 contract
# Spec: terminal `event: done` with `data: <full RecommendResponse JSON>`.
# Current code emits `{session_id, trace_id}` only. Frontend expects to render
# recommendations from this payload.
def test_sse_done_event_must_carry_recommend_response_payload():
    main_module = _fresh_main()
    client = TestClient(main_module.app)
    with client.stream("GET", "/sse?session_id=t") as r:
        body = b"".join(r.iter_bytes()).decode()

    # Find the `done` chunk
    done_chunk = next((c for c in body.split("\n\n") if "event: done" in c), None)
    assert done_chunk, f"no done frame in stream:\n{body[:600]}"

    data_line = next((l for l in done_chunk.splitlines() if l.startswith("data: ")), None)
    assert data_line
    payload = json.loads(data_line[6:])

    expected_keys = {"recommendations", "trust_calibrated", "specialty"}
    missing = expected_keys - set(payload.keys())
    assert not missing, (
        f"done event must carry RecommendResponse fields {expected_keys}; "
        f"missing {missing}. Got payload keys: {list(payload.keys())}"
    )


# BUG #13 — SSE generator doesn't abort on client disconnect
# The async generator runs through all of AGENT_ORDER even after the client
# closes the connection, leaking compute (and tokens, once real agents wired).
# Real fix: pass `request: Request` and check `await request.is_disconnected()`
# at the top of each iteration.
def test_sse_must_abort_on_client_disconnect(monkeypatch):
    main_module = _fresh_main()

    call_count = {"n": 0}
    real_evt = main_module._evt

    def counting_evt(agent, token, trace_id):
        call_count["n"] += 1
        return real_evt(agent, token, trace_id)

    monkeypatch.setattr(main_module, "_evt", counting_evt)

    async def run():
        transport = httpx.ASGITransport(app=main_module.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://t") as cli:
            async with cli.stream("GET", "/sse?session_id=t") as r:
                # consume just the initial ping then bail
                async for _ in r.aiter_bytes():
                    break
        # Give the (incorrectly) still-running generator time to finish all agents
        await asyncio.sleep(0.5)

    asyncio.run(run())

    expected_max = len(main_module.AGENT_ORDER)  # one starting evt is acceptable
    assert call_count["n"] <= expected_max, (
        f"after client disconnect, generator must stop. "
        f"_evt called {call_count['n']} times for {len(main_module.AGENT_ORDER)} agents "
        f"(would be {len(main_module.AGENT_ORDER)*2} if it ran to completion)."
    )


# BUG #14 — /sse_demo raises HTTPException 503 instead of SSE event
# Frontend EventSource expects text/event-stream. A 503 with application/json
# triggers EventSource.onerror with no payload — Arushi's panel shows
# "stream failed" with no diagnostic.
def test_sse_demo_missing_transcript_must_emit_sse_error_not_503(monkeypatch, tmp_path):
    main_module = _fresh_main()
    bogus = tmp_path / "doesnt_exist.sse"
    monkeypatch.setattr(main_module, "_DEMO_TRANSCRIPT", bogus)

    client = TestClient(main_module.app)
    r = client.get("/sse_demo?session_id=t")

    assert r.headers.get("content-type", "").startswith("text/event-stream"), (
        f"contract: must respond with text/event-stream so EventSource handles it. "
        f"Got content-type={r.headers.get('content-type')!r}, status={r.status_code}"
    )
    assert "event: error" in r.text, (
        f"contract: missing transcript must surface as event: error frame, "
        f"not as HTTPException. Body: {r.text[:300]}"
    )
