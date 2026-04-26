"""Tests for the sponsor flag bag.

Critical property: flags must be read at *access* time, not import time, so
operators can flip them without restarting the process.
"""
from __future__ import annotations

import pytest


@pytest.mark.parametrize("value,expected", [
    ("true", True),
    ("True", True),
    ("TRUE", True),
    ("1", True),
    ("yes", True),
    ("on", True),
    ("false", False),
    ("0", False),
    ("", False),
    ("anything-else", False),
])
def test_flag_parsing(monkeypatch, value, expected):
    monkeypatch.setenv("SAFE_DEMO", value)

    from app.sponsor.flags import flags

    assert flags.SAFE_DEMO is expected


def test_flag_default_when_unset(monkeypatch):
    monkeypatch.delenv("SAFE_DEMO", raising=False)

    from app.sponsor.flags import flags

    assert flags.SAFE_DEMO is False


def test_flag_re_read_per_access(monkeypatch):
    """Toggling env mid-session must take effect immediately."""
    from app.sponsor.flags import flags

    monkeypatch.setenv("SAFE_DEMO", "false")
    assert flags.SAFE_DEMO is False

    monkeypatch.setenv("SAFE_DEMO", "true")
    assert flags.SAFE_DEMO is True

    monkeypatch.setenv("SAFE_DEMO", "false")
    assert flags.SAFE_DEMO is False
