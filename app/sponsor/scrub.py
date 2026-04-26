"""Extra token-scrub patterns for sponsor secrets (extends bug #20 list).

The base pattern list lives in :mod:`app.main` and only matches Databricks
``dapi*`` tokens. Sponsor modules carry OpenAI ``sk-...`` and Fish Audio
32-hex keys — neither of which the base patterns redact.

This module is import-side-effect-free: it only exposes ``PATTERNS``. The
consumer (``app.main``) extends its own ``_TOKEN_PATTERNS`` with these. We
avoid an inverse import (``app.sponsor.scrub`` → ``app.main``) so the sponsor
package can be imported by tests without dragging the whole FastAPI app in.
"""
from __future__ import annotations

import re


PATTERNS: list[re.Pattern[str]] = [
    # OpenAI: sk-..., sk-proj-..., etc. 20+ trailing chars to avoid matching
    # arbitrary "sk-" prefixes in normal English text.
    re.compile(r"sk-[A-Za-z0-9_-]{20,}", re.IGNORECASE),
    # Fish Audio key shape: 32 lowercase hex characters. Word boundaries on
    # both sides so a 32-hex commit hash inside a URL doesn't get redacted —
    # but a bare ``11fc20c6521f4a869dc4b7cce9a5f0ea`` in a log line does.
    re.compile(r"\b[a-f0-9]{32}\b"),
]
