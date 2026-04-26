"""Real token-level SSE streaming from Databricks Foundation Model endpoints.

OpenAI-compat: FM endpoints emit `data: {choices:[{delta:{content:"..."}}]}` chunks
plus a terminal `data: [DONE]`. We strip the SSE prefix and yield the raw JSON
so the caller can re-frame it under our own event-name vocabulary (triage,
extractor, validator, router, transfer).
"""
import asyncio
import json
import logging

import httpx

from app.settings import settings

logger = logging.getLogger(__name__)


# Per-phase timeout, NOT a single 60s ceiling on the whole exchange.
# A long Llama 70B answer can stream for >60s without any single read pausing
# more than a second; a global timeout would tear it down mid-token. The
# per-read budget keeps detection of a stalled upstream while permitting the
# stream itself to run as long as tokens keep arriving.
_STREAM_TIMEOUT = httpx.Timeout(connect=10.0, read=30.0, write=10.0, pool=10.0)


async def stream_endpoint(endpoint: str, messages: list):
    async with httpx.AsyncClient(timeout=_STREAM_TIMEOUT) as cli:
        async with cli.stream(
            "POST",
            f"{settings.databricks_host}/serving-endpoints/{endpoint}/invocations",
            headers={"Authorization": f"Bearer {settings.databricks_token}"},
            json={"messages": messages, "stream": True, "temperature": 0},
        ) as resp:
            # Without raise_for_status, a 401/500 streams the HTML error body
            # as if it were SSE chunks — caller would see garbage and crash on
            # json.loads with no useful diagnostic.
            resp.raise_for_status()
            try:
                async for line in resp.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    payload = line[6:]
                    # OpenAI-compat terminal sentinel; not parseable as JSON.
                    if payload == "[DONE]":
                        return
                    # Defensive boundary: drop unparseable chunks so a single bit
                    # of LLM noise doesn't tear down the entire stream. The
                    # downstream consumer can then trust whatever we yield.
                    try:
                        json.loads(payload)
                    except json.JSONDecodeError:
                        logger.warning(
                            "llm_stream_dropped_malformed_chunk endpoint=%s payload=%s",
                            endpoint, payload[:120],
                        )
                        continue
                    yield payload
            except asyncio.CancelledError:
                # Consumer (FastAPI SSE handler) has gone away — close the
                # upstream httpx body cleanly so the underlying TCP socket isn't
                # leaked into the connection pool half-read, then re-raise so
                # the runtime can finish task cancellation properly.
                logger.info("llm_stream_cancelled endpoint=%s", endpoint)
                await resp.aclose()
                raise
