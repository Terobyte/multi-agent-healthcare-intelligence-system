"""Render the 3 text overlays as transparent PNGs for ffmpeg's overlay filter.

Used by build_demo_video.py — the local ffmpeg build is missing drawtext, so
we burn the text into PNGs ahead of time and composite them in.
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "demo_voiceover"


# Pick a Helvetica/Arial-grade font that ships with macOS.
FONT_CANDIDATES = [
    "/System/Library/Fonts/Helvetica.ttc",
    "/System/Library/Fonts/HelveticaNeue.ttc",
    "/Library/Fonts/Arial.ttf",
    "/System/Library/Fonts/Avenir.ttc",
]


def find_font() -> str:
    for p in FONT_CANDIDATES:
        if Path(p).exists():
            return p
    return ""


def render_overlay(
    text: str,
    out_name: str,
    fontsize: int,
    fg: tuple,
    canvas_w: int = 1920,
    canvas_h: int = 1080,
) -> None:
    img = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    font_path = find_font()
    if not font_path:
        font = ImageFont.load_default()
    else:
        try:
            font = ImageFont.truetype(font_path, fontsize)
        except OSError:
            font = ImageFont.load_default()

    # Measure text → derive a centred rounded-rect background.
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    pad_x, pad_y = 48, 28

    box_w = tw + 2 * pad_x
    box_h = th + 2 * pad_y
    box_x = (canvas_w - box_w) // 2
    # Place bottom-third of frame, ~280 px from bottom — same as original plan.
    box_y = canvas_h - 280 - box_h // 2

    # Semi-transparent black box.
    draw.rounded_rectangle(
        [(box_x, box_y), (box_x + box_w, box_y + box_h)],
        radius=18,
        fill=(0, 0, 0, 180),
    )

    # Centred text inside the box. Helvetica's bbox top is offset, so we
    # adjust by bbox[1] to seat the glyphs visually-centred, not just the
    # bbox-centred.
    text_x = box_x + pad_x - bbox[0]
    text_y = box_y + pad_y - bbox[1]
    draw.text((text_x, text_y), text, fill=fg, font=font)

    out_path = OUT_DIR / out_name
    img.save(out_path)
    print(f"   ✓ {out_path.name}  ({box_w}×{box_h} text box)")


def main() -> None:
    OUT_DIR.mkdir(exist_ok=True)
    print("Rendering overlays…")
    render_overlay(
        text="ATOMIC  ·  4 / 4",
        out_name="overlay_rollback.png",
        fontsize=96,
        fg=(232, 99, 74, 255),  # coral
    )
    render_overlay(
        text="Trust  0.831  →  0.350",
        out_name="overlay_trust.png",
        fontsize=88,
        fg=(159, 211, 199, 255),  # mint
    )
    render_overlay(
        text="Guide care, don't just map it.",
        out_name="overlay_close.png",
        fontsize=80,
        fg=(255, 255, 255, 255),
    )


if __name__ == "__main__":
    main()
