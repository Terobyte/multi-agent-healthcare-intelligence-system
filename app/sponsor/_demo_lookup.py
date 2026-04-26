"""Hardcoded allowlist of pre-recorded demo artifacts.

Never construct paths from user input. Routes that take a ``demo_id`` query
param check it against the keys here and 404 on miss — no ``Path / user_input``
concatenation, so no path traversal.
"""
from __future__ import annotations

from pathlib import Path
from typing import Final


_DEMO_DIR: Final[Path] = Path(__file__).parent / "_demo"

# Demo facilities pinned by `bugs.md` and `requirements2.md` allowlist.
# Each value is a Path *constructed once at import* — never derived from input.
VOICE_HI: Final[dict[str, Path]] = {
    "5603": _DEMO_DIR / "demo_voice_5603_hi.mp3",
    "8888": _DEMO_DIR / "demo_voice_8888_hi.mp3",
    "959":  _DEMO_DIR / "demo_voice_959_hi.mp3",
}

VOICE_UR: Final[dict[str, Path]] = {
    "5603": _DEMO_DIR / "demo_voice_5603_ur.mp3",
    "8888": _DEMO_DIR / "demo_voice_8888_ur.mp3",
    "959":  _DEMO_DIR / "demo_voice_959_ur.mp3",
}

# Canned data files for non-voice features.
GENIE_CANNED: Final[Path] = _DEMO_DIR / "demo_genie_canned.json"


def voice_path(demo_id: str, lang: str) -> Path | None:
    """Return the pre-recorded voice file for a demo facility, or None."""
    table = VOICE_HI if lang == "hi" else VOICE_UR if lang == "ur" else None
    if table is None:
        return None
    return table.get(demo_id)
