"""Real token-level SSE streaming from Databricks Foundation Model endpoints.

OpenAI-compat: FM endpoints emit `data: {choices:[{delta:{content:"..."}}]}` chunks
plus a terminal `data: [DONE]`. We strip the SSE prefix and yield the raw JSON
so the caller can re-frame it under our own event-name vocabulary (triage,
extractor, validator, router, transfer).
"""
import httpx

from app.settings import settings


async def stream_endpoint(endpoint: str, messages: list):
    async with httpx.AsyncClient(timeout=60) as cli:
        async with cli.stream(
            "POST",
            f"{settings.databricks_host}/serving-endpoints/{endpoint}/invocations",
            headers={"Authorization": f"Bearer {settings.databricks_token}"},
            json={"messages": messages, "stream": True, "temperature": 0},
        ) as resp:
            try:
                async for line in resp.aiter_lines():
                    if line.startswith("data: "):
                        yield line[6:]
            finally:
                await resp.aclose()
