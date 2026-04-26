"""Failing tests for known SSE + config bugs.

Each test FAILS on current code. Committing these locks in the regression so
when someone fixes the bug, the test flips green.

See bugs.md for triage. Bugs covered: #5, #14.
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


# BUG — SSE heartbeat is agent-completion-driven, not wall-clock-driven
# `app/main.py` ~L230-239: the ping check `if time.time() - last_ping > 15:` runs
# AFTER each agent step. When agents are FAST (the demo cadence is ~0.2s/agent,
# ~1s total for all 5), the >15s gate never trips and only the *initial* ping
# fires. nginx / Render LB / Cloudflare close idle SSE streams at ~30-60s of
# silence, so under real model latency variance + a slow first token the panel
# hangs with no diagnostic. Correct impl: a parallel `asyncio.create_task` that
# emits `event: ping` on a wall-clock cadence regardless of agent emission.
def test_bug_heartbeat_sends_unconditionally_on_wall_clock_interval(monkeypatch):
    """Pings must fire on wall-clock cadence, even when agents complete fast.

    We stretch the wall-clock window to ~3s by emitting 5 fast tokens at 0.5s
    each, then assert ≥2 ping frames were emitted. With the current buggy code
    the >15s gate never trips inside the agent loop, so only the single initial
    ping is present and this test FAILS — locking in the regression.
    """
    main_module = _fresh_main()

    # 5 tokens × 0.5s = 2.5s of stream time. Long enough that ≥2 wall-clock pings
    # at any reasonable cadence (say, every 1s) MUST appear if the heartbeat is
    # actually wall-clock-driven. Short enough that the test runs in ~3s real.
    # Use the real Literal-validated agent names so ReasoningPanelEvent doesn't
    # fail validation mid-loop. The bug is in the heartbeat scheduler, not in
    # the agent vocabulary.
    monkeypatch.setattr(
        main_module, "AGENT_ORDER",
        ["triage", "extractor", "validator", "router", "transfer"],
    )

    real_sleep = asyncio.sleep
    orig_time = main_module.time.time

    async def fast_sleep(_secs):
        # Each agent step waits 0.5s real time — fast enough to never hit the
        # buggy >15s gate, slow enough that any sane wall-clock pinger fires.
        await real_sleep(0.5)

    monkeypatch.setattr(main_module.asyncio, "sleep", fast_sleep)
    # Leave time.time() real — we WANT real elapsed wall-clock so a correct
    # implementation (parallel task on real timer) would emit pings naturally.

    client = TestClient(main_module.app)
    with client.stream("GET", "/sse?session_id=hb") as r:
        body = b"".join(r.iter_bytes()).decode()

    ping_count = body.count("event: ping")
    # ≥2 means: initial ping (if any) PLUS at least one wall-clock-driven ping
    # during the ~2.5s of fast agent emission. Buggy code emits exactly 1.
    assert ping_count >= 2, (
        f"Heartbeat must be wall-clock-driven, not agent-completion-driven. "
        f"Over ~2.5s of fast-agent streaming, expected ≥2 ping frames "
        f"(initial + ≥1 from a parallel asyncio.create_task heartbeat). "
        f"Got {ping_count}. Proxy idle-close (~30-60s) will silently kill the "
        f"connection if pings depend on agents finishing. Body:\n{body[:800]}"
    )


# BUG — LLM streaming parser kills the SSE stream on a single malformed chunk
# app/agents/reasoning_stream.py:25-32 — the loop yields raw `data: ...`
# payloads without validating that they are parseable JSON. Databricks FM
# endpoints (mlflow OpenAI-compat) occasionally emit garbage tokens, partial
# JSON, or vendor sentinels that aren't `[DONE]`. The current code yields the
# bad payload as-is to the caller, which then explodes inside json.loads —
# but the contract from the audit is that stream_endpoint should be the
# defensive boundary: malformed JSON chunks must be SKIPPED (warn, don't
# raise) so the stream survives transient LLM noise and the next good chunk
# still reaches the user. Test below proves: a bad chunk wedged between two
# good ones must NOT prevent the trailing good chunk from being observed by
# a normal consumer iterating the generator.
def test_bug_llm_stream_continues_on_malformed_json_chunk(monkeypatch):
    from app.agents import reasoning_stream

    good_before = '{"choices":[{"delta":{"content":"hello"}}]}'
    bad_middle = '{"choices": [{'  # truncated JSON — json.loads raises
    good_after = '{"choices":[{"delta":{"content":"world"}}]}'

    sse_lines = [
        f"data: {good_before}",
        f"data: {bad_middle}",
        f"data: {good_after}",
        "data: [DONE]",
    ]

    class FakeResponse:
        def raise_for_status(self):
            return None

        async def aiter_lines(self):
            for ln in sse_lines:
                yield ln

        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

    class FakeClient:
        def __init__(self, *a, **kw):
            pass

        def stream(self, *a, **kw):
            return FakeResponse()

        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

    monkeypatch.setattr(reasoning_stream.httpx, "AsyncClient", FakeClient)

    contents: list[str] = []

    async def consume():
        # Mirror the real consumer (app/agents/triage.py:208-215): iterate
        # stream_endpoint and json.loads each payload. The audit contract is
        # that stream_endpoint already filters non-JSON, so the consumer can
        # trust whatever it yields. Today it doesn't, so the bad payload
        # propagates and json.loads raises mid-iteration, killing the loop
        # before `good_after` is ever observed.
        async for raw in reasoning_stream.stream_endpoint("triage", []):
            obj = json.loads(raw)
            delta = obj["choices"][0]["delta"].get("content", "")
            if delta:
                contents.append(delta)

    asyncio.run(consume())

    assert "hello" in contents, (
        f"pre-bad-chunk content must be emitted; got contents={contents}"
    )
    assert "world" in contents, (
        "post-bad-chunk content must still be emitted — a single malformed "
        "JSON chunk in the middle of an LLM stream must NOT terminate the "
        "stream. stream_endpoint is the defensive boundary and must skip "
        f"unparseable payloads with a warning. Got contents={contents}"
    )
