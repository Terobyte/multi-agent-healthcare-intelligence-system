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


# bug #108 was: the bare 32-hex pattern redacted legitimate transaction ids.
# bug #9 (sweep #2) was: my first fix went the other way — *only* redacting
# when a Fish-key context prefix was present, so a raw key dump would leak.
# Defense in depth: redact every 32-hex string EXCEPT when it is obviously a
# transaction id (UUID-with-hyphens form, or preceded by a known-safe key
# like "transaction_id=" / "txn=" / "feedback_id=fb_").
_SAFE_HEX_CONTEXTS = re.compile(
    r"(?i)(?:transaction[_-]?id|txn[_-]?id|trace[_-]?id|message[_-]?id|"
    r"correlation[_-]?id|request[_-]?id|conversation[_-]?id|"
    r"feedback[_-]?id\s*=\s*fb_|sha256\s*=)\s*[:=]?\s*[a-f0-9]{32}\b"
)


def _redact_hex32_with_safelist(s: str, replacement: str = "<redacted>") -> str:
    """Replace bare 32-hex strings except when prefixed with a known-safe key.

    Used by :func:`apply_sponsor_patterns` so the sponsor secret-scrubber stays
    aggressive on raw key dumps while preserving audit identifiers in logs.
    """
    # Mark safe occurrences so the bare-hex pattern below skips them.
    sentinels: list[str] = []

    def _stash(m: re.Match[str]) -> str:
        sentinels.append(m.group(0))
        return f"\x00SAFE_HEX_{len(sentinels) - 1}\x00"

    masked = _SAFE_HEX_CONTEXTS.sub(_stash, s)
    cleaned = re.sub(r"\b[a-f0-9]{32}\b", replacement, masked)
    for i, original in enumerate(sentinels):
        cleaned = cleaned.replace(f"\x00SAFE_HEX_{i}\x00", original, 1)
    return cleaned


PATTERNS: list[re.Pattern[str]] = [
    # OpenAI: sk-..., sk-proj-..., etc. 20+ trailing chars to avoid matching
    # arbitrary "sk-" prefixes in normal English text.
    re.compile(r"sk-[A-Za-z0-9_-]{20,}", re.IGNORECASE),
    # Fish Audio key shape: 32 lowercase hex characters, but only when NOT
    # appearing in a known-safe transaction-id / trace-id context. The
    # actual conditional skip happens in ``_redact_hex32_with_safelist`` —
    # PATTERNS keeps the bare regex for any legacy callers that walk it
    # directly (the sponsor logger uses the helper).
    re.compile(r"\b[a-f0-9]{32}\b"),
]


def apply_sponsor_patterns(s: str) -> str:
    """Run all sponsor scrub patterns on ``s`` and return the redacted text.

    Use this from logger filters / response serializers — preferred over a raw
    PATTERNS loop because it applies the safe-list before the bare-hex regex.
    """
    if not s:
        return s
    # OpenAI keys never appear in audit identifiers, so straightforward.
    s = PATTERNS[0].sub("<redacted>", s)
    # Hex32 needs context-aware handling.
    s = _redact_hex32_with_safelist(s)
    return s
