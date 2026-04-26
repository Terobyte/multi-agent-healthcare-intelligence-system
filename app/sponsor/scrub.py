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
    # bug #108: the previous bare 32-hex pattern matched legitimate MD5
    # hashes / transaction IDs / UUID-no-hyphens that healthcare audit logs
    # rely on (every booking writes transaction_id=<32-hex> lines). Require
    # an explicit Fish Audio context — `fish_key=`, `apiKey=`, `Fish-Key:`,
    # an `Authorization: Bearer ` shape, or the literal `FISH_API_KEY`
    # environment-variable token — before redacting. Real Fish Audio keys
    # always appear next to one of these markers in our logs; bare 32-hex
    # strings without context are almost certainly transaction IDs.
    re.compile(
        r"(?i)(?:fish[_-]?(?:api[_-]?)?key|FISH_API_KEY|apikey|api[_-]key|"
        r"authorization\s*:\s*bearer)[\s:=]+[a-f0-9]{32}\b"
    ),
]
