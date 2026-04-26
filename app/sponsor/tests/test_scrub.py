"""Tests for the sponsor token-scrub patterns.

The patterns must be merged into ``app.main._TOKEN_PATTERNS`` so the global
log-record factory (set up in ``app.main``) redacts OpenAI ``sk-...`` and
Fish Audio 32-hex keys before they reach a handler.
"""
from __future__ import annotations

import logging
import os

# Force offline mode so importing app.main doesn't try to reach Databricks.
os.environ.setdefault("VS_ENDPOINT", "")


def test_patterns_module_exposes_list():
    from app.sponsor.scrub import PATTERNS

    assert isinstance(PATTERNS, list)
    assert len(PATTERNS) == 2


def test_main_extends_token_patterns_with_sponsor_patterns():
    from app import main

    pattern_strs = [p.pattern for p in main._TOKEN_PATTERNS]
    assert any("sk-" in s for s in pattern_strs)
    assert any("a-f0-9" in s and "32" in s for s in pattern_strs)


def test_openai_key_is_redacted():
    from app import main

    fake = "log line with sk-proj-AAAABBBBCCCCDDDDEEEEFFFFGGGG token here"
    redacted = main._scrub(fake)

    assert "sk-proj-" not in redacted
    assert "[REDACTED]" in redacted


def test_fish_32_hex_key_is_redacted():
    from app import main

    fake = "leaked key 11fc20c6521f4a869dc4b7cce9a5f0ea in log"
    redacted = main._scrub(fake)

    assert "11fc20c6521f4a869dc4b7cce9a5f0ea" not in redacted
    assert "[REDACTED]" in redacted


def test_short_hex_string_is_not_redacted():
    """Word-boundary anchor: short hex strings (< 32 chars) must pass through."""
    from app import main

    fake = "log with deadbeef in it"
    redacted = main._scrub(fake)

    assert "deadbeef" in redacted
