"""Assemble the 60-second AarogyaNet demo video.

Inputs:
    demo_voiceover/screen.mov   — your screen-cast (any length ≥ 60 s)
    demo_voiceover/01_hook.mp3 ... 06_close.mp3 — Fish Audio fragments

Output:
    AarogyaNet_Demo_60s.mp4

What it does:
    1. Builds a 60-second audio track by placing each fragment at a fixed
       timecode with silence padding in between.
    2. Trims the screen recording to 60 s, scales to 1920×1080.
    3. Burns three text overlays at the key wow moments:
         • 28–32 s   ROLLBACK · 4 / 4
         • 36–46 s   0.831 → 0.350
         • 55–58 s   Guide care, don't just map it.
    4. Encodes H.264 + AAC, browser-safe.

Usage:
    python3 scripts/build_demo_video.py
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
VOICE_DIR = ROOT / "demo_voiceover"
OUTPUT = ROOT / "AarogyaNet_Demo_60s.mp4"


@dataclass
class Segment:
    start: float       # seconds — when the audio starts
    file: str          # filename inside demo_voiceover/


# Real-voice fragments. Hook + hospitals are fused (recording 12), scene 3
# was re-recorded after the tile-name correction (Bed/Oxygen/Drug/Specialist),
# scenes 4-6 came from recording 11 with internal silences compressed.
SEGMENTS: list[Segment] = [
    Segment(start=0.0,  file="v2_s12_c.mp3"),         # hook + hospitals (10.5 s)
    Segment(start=12.0, file="03_atomic_saga_v2.mp3"),# atomic saga (16.6 s)
    Segment(start=32.0, file="v2_s4_c.mp3"),          # trust loop (13.6 s)
    Segment(start=47.0, file="v2_s5_c.mp3"),          # NGO (7.5 s)
    Segment(start=57.5, file="v2_s6_c.mp3"),          # close (1.6 s)
]

TOTAL_DURATION = 60.0


@dataclass
class Overlay:
    """Pre-rendered PNG overlay (this ffmpeg build lacks drawtext)."""
    png: str        # filename inside demo_voiceover/
    start: float
    end: float


OVERLAYS: list[Overlay] = [
    Overlay(png="overlay_rollback.png", start=28.0, end=32.0),
    Overlay(png="overlay_trust.png",    start=36.0, end=46.0),
    Overlay(png="overlay_close.png",    start=55.0, end=60.0),
]


def find_screen_recording() -> Path:
    """Pick the user's screen-cast — first match wins."""
    candidates = [
        VOICE_DIR / "screen.mov",
        VOICE_DIR / "screen.mp4",
        VOICE_DIR / "demo.mov",
        VOICE_DIR / "demo.mp4",
    ]
    for c in candidates:
        if c.exists():
            return c
    # Fall back to *any* mov / mp4 in the dir
    for ext in ("*.mov", "*.mp4"):
        hits = sorted(VOICE_DIR.glob(ext))
        if hits:
            return hits[0]
    print(f"\n✗ No screen recording found in {VOICE_DIR}")
    print("  Drop your QuickTime recording as 'screen.mov' and re-run.")
    sys.exit(1)


def build_audio_filter() -> str:
    """Pad each fragment with leading silence so they line up at SEGMENTS[i].start.

    Result: a single 60-second mono-mixed audio stream as label [aout].
    """
    parts: list[str] = []
    mix_inputs: list[str] = []
    # Inputs 1..6 are the mp3 fragments (input 0 is the video).
    for i, seg in enumerate(SEGMENTS, start=1):
        delay_ms = int(seg.start * 1000)
        label = f"a{i}"
        # adelay: prepends silence to the front of the fragment.
        # apad=whole_dur sets the absolute total length so the fragment
        # ends with silence instead of clipping the mix early.
        parts.append(
            f"[{i}:a]adelay={delay_ms}|{delay_ms},"
            f"apad=whole_dur={TOTAL_DURATION}[{label}]"
        )
        mix_inputs.append(f"[{label}]")
    parts.append(
        f"{''.join(mix_inputs)}amix=inputs={len(SEGMENTS)}:"
        f"duration=first:dropout_transition=0,"
        f"atrim=0:{TOTAL_DURATION},asetpts=N/SR/TB[aout]"
    )
    return ";".join(parts)


def build_filter_complex() -> str:
    """Trim/scale base video, then composite each overlay PNG at its window.

    Inputs:
        [0:v]   = base screen recording
        [N:v]   = each overlay PNG (N = 1 + len(SEGMENTS) + i)
    Audio inputs sit between the video and the PNG inputs; the index math
    in main() lines them up.
    """
    base_chain = [
        f"trim=0:{TOTAL_DURATION}",
        "setpts=PTS-STARTPTS",
        "scale=1920:1080:force_original_aspect_ratio=decrease",
        "pad=1920:1080:(ow-iw)/2:(oh-ih)/2:black",
    ]
    parts = [f"[0:v]{','.join(base_chain)}[base]"]
    cur_label = "base"
    overlay_input_offset = 1 + len(SEGMENTS)  # video + audio fragments
    for i, ov in enumerate(OVERLAYS):
        in_idx = overlay_input_offset + i
        next_label = f"v{i}"
        parts.append(
            f"[{cur_label}][{in_idx}:v]"
            f"overlay=x=(W-w)/2:y=H-h-120:"
            f"enable='between(t,{ov.start},{ov.end})'[{next_label}]"
        )
        cur_label = next_label
    parts.append(f"[{cur_label}]copy[vout]")
    return ";".join(parts)


def main() -> None:
    if shutil.which("ffmpeg") is None:
        print("✗ ffmpeg not found in PATH. Install with: brew install ffmpeg")
        sys.exit(1)

    # Pre-flight: every audio fragment must exist.
    missing = [s.file for s in SEGMENTS if not (VOICE_DIR / s.file).exists()]
    if missing:
        print(f"✗ Missing audio fragments: {', '.join(missing)}")
        print("  Run scripts/gen_demo_voiceover.py first.")
        sys.exit(1)

    screen = find_screen_recording()
    print(f"→ Screen recording: {screen.name}")
    print(f"→ Voice fragments:  {len(SEGMENTS)}")
    print(f"→ Output:           {OUTPUT.name}")
    print()

    audio_filter = build_audio_filter()
    video_chain = build_filter_complex()
    full_filter = f"{video_chain};{audio_filter}"

    cmd: list[str] = ["ffmpeg", "-y", "-i", str(screen)]
    for seg in SEGMENTS:
        cmd += ["-i", str(VOICE_DIR / seg.file)]
    for ov in OVERLAYS:
        cmd += ["-i", str(VOICE_DIR / ov.png)]
    cmd += [
        "-filter_complex", full_filter,
        "-map", "[vout]",
        "-map", "[aout]",
        "-t", str(TOTAL_DURATION),
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "20",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        "-movflags", "+faststart",
        str(OUTPUT),
    ]

    print("Running ffmpeg…\n")
    rc = subprocess.call(cmd)
    if rc != 0:
        print(f"\n✗ ffmpeg exited with code {rc}")
        sys.exit(rc)

    size_mb = OUTPUT.stat().st_size / (1024 * 1024)
    print(f"\n✓ Wrote {OUTPUT.name}  ({size_mb:.1f} MB)")
    print(f"  Open with: open {OUTPUT}")


if __name__ == "__main__":
    main()
