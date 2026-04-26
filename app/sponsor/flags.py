"""Request-time env-flag reader for the sponsor stack.

Flags are evaluated on every access (not cached at import) so an operator can
flip ``SAFE_DEMO`` or ``SPONSOR_GENIE_LIVE`` without restarting the process.
That matters on stage where rehearsal flips happen seconds before the demo.
"""
from __future__ import annotations

import os


def _read(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


class _Flags:
    """Property bag whose getters re-read os.environ on each call."""

    @property
    def SPONSOR_AGENT_BRICKS(self) -> bool:
        return _read("SPONSOR_AGENT_BRICKS")

    @property
    def SPONSOR_GENIE(self) -> bool:
        return _read("SPONSOR_GENIE")

    @property
    def SPONSOR_GENIE_LIVE(self) -> bool:
        return _read("SPONSOR_GENIE_LIVE")

    @property
    def SPONSOR_VOICE(self) -> bool:
        return _read("SPONSOR_VOICE")

    @property
    def SPONSOR_KA(self) -> bool:
        return _read("SPONSOR_KA")

    @property
    def SAFE_DEMO(self) -> bool:
        # Master kill-switch: if true, all sponsor routes serve canned artifacts
        # and never touch a live API. Reads on every call so a stage flip from
        # `0` to `1` takes effect immediately.
        return _read("SAFE_DEMO")


flags = _Flags()
