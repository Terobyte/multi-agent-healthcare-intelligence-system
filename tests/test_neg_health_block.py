"""Negative test: /health blocks the asyncio event loop.

The handler at app/main.py:177 is `def health()` (sync) calling `_fm_endpoint_count()`
which in turn does `future.result(timeout=8.0)`. When uvicorn dispatches a sync
route, FastAPI runs it in a threadpool — but if the handler awaits/blocks on a
slow upstream, **all** concurrent requests still pile up against the threadpool
worker count and effectively serialize behind the same blocking call.

The proper fix is either:
  (a) `async def health()` that uses `asyncio.to_thread` / `run_in_executor`
      with proper await semantics, OR
  (b) the blocking `_fm_endpoint_count()` itself becomes awaitable / non-blocking.

This test proves the current implementation does NEITHER: it's a sync `def`
handler that calls a sync, blocking helper. RED on current code.
"""
from __future__ import annotations

import ast
import importlib
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest


MAIN_PY = Path(__file__).resolve().parent.parent / "app" / "main.py"


def _find_health_handler(tree: ast.Module) -> ast.FunctionDef | ast.AsyncFunctionDef | None:
    """Locate the function decorated with @app.get('/health')."""
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for deco in node.decorator_list:
            # @app.get("/health") -> Call(func=Attribute(attr='get'), args=[Constant('/health')])
            if (
                isinstance(deco, ast.Call)
                and isinstance(deco.func, ast.Attribute)
                and deco.func.attr == "get"
                and deco.args
                and isinstance(deco.args[0], ast.Constant)
                and deco.args[0].value == "/health"
            ):
                return node
    return None


def _calls_in(node: ast.AST) -> list[ast.Call]:
    return [n for n in ast.walk(node) if isinstance(n, ast.Call)]


def _has_async_offload(handler: ast.AST) -> bool:
    """True if the handler offloads blocking work via async-aware machinery."""
    # Walk the body and look for any of:
    #   - asyncio.to_thread(...)
    #   - loop.run_in_executor(...) / get_event_loop().run_in_executor(...)
    #   - anyio.to_thread.run_sync(...) / starlette.concurrency.run_in_threadpool(...)
    needles = {
        "to_thread",          # asyncio.to_thread / anyio.to_thread.run_sync
        "run_in_executor",    # loop.run_in_executor
        "run_in_threadpool",  # starlette.concurrency.run_in_threadpool
        "run_sync",           # anyio.to_thread.run_sync
    }
    for call in _calls_in(handler):
        func = call.func
        # bare name: to_thread(...)
        if isinstance(func, ast.Name) and func.id in needles:
            return True
        # attribute: x.to_thread(...) / asyncio.to_thread(...) / loop.run_in_executor(...)
        if isinstance(func, ast.Attribute) and func.attr in needles:
            return True
    return False


def _calls_blocking_endpoint_count(handler: ast.AST) -> bool:
    """True if the handler calls `_fm_endpoint_count(...)` directly in its body."""
    for call in _calls_in(handler):
        func = call.func
        if isinstance(func, ast.Name) and func.id == "_fm_endpoint_count":
            return True
        if isinstance(func, ast.Attribute) and func.attr == "_fm_endpoint_count":
            return True
    return False


@pytest.fixture(scope="module")
def health_handler() -> ast.AST:
    src = MAIN_PY.read_text()
    tree = ast.parse(src)
    handler = _find_health_handler(tree)
    assert handler is not None, "could not locate @app.get('/health') handler in app/main.py"
    return handler


def test_health_does_not_block_event_loop(health_handler: ast.AST) -> None:
    """The /health handler must not synchronously block on `_fm_endpoint_count()`.

    Acceptable shapes:
      1. `async def health(...)` AND offloads via to_thread / run_in_executor /
         run_in_threadpool / run_sync.
      2. `def health(...)` but the call to `_fm_endpoint_count()` is wrapped in
         async-offload machinery (rare for a sync handler, but allowed).

    Currently: sync `def health()` calling sync `_fm_endpoint_count()` which
    itself does `future.result(timeout=8.0)`. Under load, this saturates the
    Starlette threadpool and stalls every concurrent request behind the 8s
    timeout. RED until refactored.
    """
    is_async = isinstance(health_handler, ast.AsyncFunctionDef)
    has_offload = _has_async_offload(health_handler)
    calls_blocking = _calls_blocking_endpoint_count(health_handler)

    # Shape 1: async handler with proper offload.
    shape_1 = is_async and has_offload
    # Shape 2: sync handler but the blocking call is wrapped in offload machinery.
    shape_2 = (not is_async) and has_offload and calls_blocking

    assert shape_1 or shape_2, (
        "/health handler blocks the event loop: it is "
        f"{'async' if is_async else 'sync'} def, "
        f"calls _fm_endpoint_count={calls_blocking}, "
        f"uses async-offload machinery={has_offload}. "
        "Refactor to `async def health()` + `await asyncio.to_thread(_fm_endpoint_count)` "
        "(or equivalent) so the 8s `future.result(timeout=8.0)` cannot serialize "
        "concurrent /health probes behind a single threadpool worker."
    )


def test_health_endpoint_concurrency_runtime() -> None:
    """Runtime confirmation: 5 concurrent /health calls should NOT serialize.

    We monkey-patch `_fm_endpoint_count` to sleep 5s, then fire 5 concurrent
    /health requests. If the handler properly offloads, total wall time should
    be < 8s (one ~5s sleep, fanned out). If it serializes (current bug), total
    wall time will be much higher, OR — because FastAPI runs sync handlers in
    its bounded threadpool — at least confirm the handler does not pin a
    single worker for the whole 5s.

    Heuristic threshold: 5 concurrent calls × 5s sleep should finish in well
    under 8s if concurrent. Current sync handler will (depending on threadpool
    size, default 40) sometimes pass — so this test is BEST-EFFORT. The AST
    test above is the authoritative guard. We still keep this so a regression
    where the threadpool is exhausted (or the call is serialized via a lock)
    surfaces visibly.
    """
    os.environ["AAROGYANET_DEV"] = "1"
    import app.main as main_module
    importlib.reload(main_module)

    from fastapi.testclient import TestClient

    sleep_seconds = 5.0

    def slow_count(*_args, **_kwargs):
        time.sleep(sleep_seconds)
        return 1

    main_module._fm_endpoint_count = slow_count  # type: ignore[assignment]
    # Bust the TTL cache so every call hits the slow path.
    main_module._ep_cache["n"] = None
    main_module._ep_cache["ts"] = 0.0

    client = TestClient(main_module.app)

    N = 5

    def hit() -> int:
        return client.get("/health").status_code

    start = time.perf_counter()
    with ThreadPoolExecutor(max_workers=N) as pool:
        results = list(pool.map(lambda _: hit(), range(N)))
    elapsed = time.perf_counter() - start

    assert all(rc == 200 for rc in results), f"non-200 codes: {results}"

    # If the handler offloads correctly, all 5 sleep concurrently and total
    # wall time hovers near 5s. We allow generous slack (8s) — the bug is
    # serialization that pushes total time to N * sleep_seconds = 25s.
    assert elapsed < 8.0, (
        f"/health appears to serialize concurrent requests: {N} concurrent calls "
        f"to a 5s-sleeping `_fm_endpoint_count` took {elapsed:.2f}s "
        f"(expected <8s if properly async-offloaded). This indicates the sync "
        f"handler + sync `future.result(timeout=8.0)` is starving the threadpool."
    )
