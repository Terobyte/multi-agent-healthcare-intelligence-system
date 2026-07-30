"""Generate the 60-second demo voiceover via Fish Audio TTS.

Outputs 6 MP3 fragments to ``demo_voiceover/`` keyed by scene number so the
editor can drag them onto the iMovie timeline in order.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, "/Users/terobyte/Desktop/Projects/Active/scripts")

from library.tts_fish_audio import tts_fish_audio  # noqa: E402


OUT = Path(__file__).resolve().parent.parent / "demo_voiceover"
OUT.mkdir(exist_ok=True)


SCENES: list[tuple[str, str, str]] = [
    (
        "01_hook",
        "0-6s",
        "Mumbai. Chest pain. Triage in two seconds.",
    ),
    (
        "02_hospitals",
        "6-12s",
        "Three hospitals. Verified. Single source. Disagreement. "
        "Most demos hide this. We surface it.",
    ),
    (
        "03_atomic_saga",
        "12-38s",
        "Watch what happens when she taps Reserve. "
        "Bed. Doctor. Drug. "
        "Ambulance fails. And all four roll back. "
        "No partial promise. No partial charge. "
        "This is the discipline most hackathon chatbots cannot do.",
    ),
    (
        "04_trust_loop",
        "38-50s",
        "And after the patient leaves, trust is recomputed. "
        "Aradhna Clinic started at zero point eight three one. "
        "Six bad outcomes later, zero point three five zero. "
        "The map gets smarter every week.",
    ),
    (
        "05_ngo",
        "50-58s",
        "And the same data, flipped, exposes what is missing. "
        "Bihar: one hundred and forty-nine PIN codes "
        "with zero oncology coverage.",
    ),
    (
        "06_close",
        "58-60s",
        "Guide care. Don't just map it.",
    ),
]


def main() -> None:
    # The Fish wrapper hardcodes /tmp/ as parent — pass a bare filename then
    # move into demo_voiceover/.
    import shutil
    for name, timing, text in SCENES:
        filename = f"{name}.mp3"
        target = OUT / filename
        print(f"[{timing}]  {name}  ({len(text)} chars)")
        result = tts_fish_audio(
            text=text,
            voice_code="JLM4.7",
            force_voice=True,
            output_path=filename,
            speed=1.0,
            temperature=0.5,
        )
        if result is None:
            print(f"   ✗ FAILED — TTS returned None")
            continue
        src = Path(result)
        if not src.exists():
            print(f"   ✗ FAILED — file not at {src}")
            continue
        shutil.move(str(src), str(target))
        size_kb = target.stat().st_size / 1024
        print(f"   ✓ {target.name}  ({size_kb:.0f} KB)")
    print(f"\nAll fragments → {OUT}")


if __name__ == "__main__":
    main()
