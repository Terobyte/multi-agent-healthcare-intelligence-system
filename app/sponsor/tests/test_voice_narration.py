"""Tests for Fish Audio TTS narration — file-path and template behavior.

Live sidecar path is not exercised here (no Node process running in CI).
"""
from __future__ import annotations

import io
from pathlib import Path

import pytest


@pytest.fixture
def demo_dir(tmp_path: Path, monkeypatch) -> Path:
    """Re-point the voice lookup at a tmp dir so tests don't depend on real MP3s."""
    fake_dir = tmp_path / "_demo"
    fake_dir.mkdir()
    # Write a tiny fake MP3 — content doesn't matter, just needs to be readable.
    (fake_dir / "demo_voice_5603_hi.mp3").write_bytes(b"\xff\xfb\x90\x00" + b"\x00" * 256)

    from app.sponsor import _demo_lookup as lookup

    monkeypatch.setitem(lookup.VOICE_HI, "5603", fake_dir / "demo_voice_5603_hi.mp3")
    return fake_dir


def test_render_template_hindi():
    from app.sponsor.voice_narration import render_template

    text = render_template("hi", hospital_name="Apollo Mumbai", eta_min=14)
    assert "Apollo Mumbai" in text
    assert "14" in text
    # Sanity check: contains Devanagari characters.
    assert any("\u0900" <= ch <= "\u097f" for ch in text)


def test_render_template_urdu():
    from app.sponsor.voice_narration import render_template

    text = render_template("ur", hospital_name="AIIMS Delhi", eta_min=8)
    assert "AIIMS Delhi" in text
    assert "8" in text
    # Urdu uses Arabic-script range U+0600-U+06FF.
    assert any("\u0600" <= ch <= "\u06ff" for ch in text)


def test_render_template_falls_back_to_english_for_unknown_lang():
    from app.sponsor.voice_narration import render_template

    text = render_template("xx", hospital_name="Hosp", eta_min=5)
    assert "Hosp" in text
    assert "5 minutes" in text


def test_narrate_serves_prebaked_file(demo_dir):
    from app.sponsor.voice_narration import narrate

    media, body = narrate(demo_id="5603", lang="hi")
    assert media == "audio/mpeg"
    bytes_out = b"".join(body)
    assert bytes_out.startswith(b"\xff\xfb")  # MPEG sync word


def test_narrate_raises_when_file_missing_and_live_off():
    from app.sponsor.voice_narration import VoiceUnavailable, narrate

    with pytest.raises(VoiceUnavailable):
        narrate(demo_id="not-on-allowlist", lang="hi")


def test_narrate_safe_demo_uses_file_path(demo_dir, monkeypatch):
    monkeypatch.setenv("SAFE_DEMO", "true")
    monkeypatch.setenv("SPONSOR_VOICE", "true")

    from app.sponsor.voice_narration import narrate

    media, body = narrate(demo_id="5603", lang="hi")
    assert media == "audio/mpeg"
    # SAFE_DEMO must hit the file even if sidecar would otherwise be tried.
    assert b"".join(body).startswith(b"\xff\xfb")


def test_narrate_rejects_unknown_demo_id():
    from app.sponsor.voice_narration import VoiceUnavailable, narrate

    # ../../etc/passwd kind of input — the allowlist dict makes this trivially
    # safe, but the test pins the behavior.
    with pytest.raises(VoiceUnavailable):
        narrate(demo_id="../../etc/passwd", lang="hi")
