"""Matrix-style binary rain banner as a looping GIF (no text, so it never goes stale).

GIF is the one animated image format that plays everywhere GitHub shows a
README: every browser and the GitHub mobile apps.
"""

from __future__ import annotations

import io
import random
from pathlib import Path

from fontTools.ttLib import TTFont
from PIL import Image, ImageDraw, ImageFont

FONT_DIR = Path(__file__).parent / "fonts"
BG, LINE, GREEN, HOT = "#020a04", "#0f3d1f", "#05ff62", "#b8ffd0"  # CRT glass, frame, phosphor, glyph head

W, H = 900, 220           # pixels; shown full width at the top of the README
CELL_W, CELL_H = 14, 16   # one glyph per cell
FRAMES, FRAME_MS = 42, 80  # ~3.4 s seamless loop
LEVELS = 14               # brightness steps of the falling trails


def _rgb(hex_: str) -> tuple[int, int, int]:
    return tuple(int(hex_[i:i + 2], 16) for i in (1, 3, 5))


def _palette() -> list[int]:
    """index 0: transparent corners, 1: background, 2: frame line, 3: head glyph, 4..: trail shades."""
    bg, green = _rgb(BG), _rgb(GREEN)
    cols = [(0, 0, 0), bg, _rgb(LINE), _rgb(HOT)]
    for i in range(1, LEVELS + 1):
        t = (i / LEVELS) ** 1.4
        cols.append(tuple(round(b + (g - b) * t) for b, g in zip(bg, green)))
    flat = [v for c in cols for v in c]
    return flat + [0] * (768 - len(flat))


def _font(size: int) -> ImageFont.FreeTypeFont:
    tt = TTFont(FONT_DIR / "VT323-Regular.woff2")
    tt.flavor = None  # woff2 -> plain TrueType that Pillow can read
    buf = io.BytesIO()
    tt.save(buf)
    buf.seek(0)
    return ImageFont.truetype(buf, size)


def render(path: Path, seed: int = 1999) -> None:
    rnd = random.Random(seed)
    font = _font(20)
    cols, rows = (W - 16) // CELL_W, H // CELL_H + 1  # keep glyphs off the rounded border
    x0 = (W - cols * CELL_W) / 2
    streams = []
    for c in range(cols):
        tail = rnd.randint(5, 13)
        length = rows + tail + rnd.randint(0, 14)  # cells per lap, incl. a gap before the next drop
        laps = 1 if rnd.random() < 0.75 else 2      # whole laps per loop keeps the GIF seamless
        streams.append((tail, length, laps, rnd.uniform(0, length)))
    bits = [[rnd.getrandbits(FRAMES // 3) for _ in range(rows)] for _ in range(cols)]

    # rounded card shape (corners transparent)
    mask = Image.new("L", (W, H), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, W - 1, H - 1), radius=10, fill=255)

    frames = []
    for f in range(FRAMES):
        im = Image.new("P", (W, H), 1)
        im.putpalette(_palette())
        d = ImageDraw.Draw(im)
        for c, (tail, length, laps, off) in enumerate(streams):
            head = int(off + f * laps * length / FRAMES) % length
            for k in range(tail + 1):
                r = head - k
                if not 0 <= r < rows:
                    continue
                # fade the trail, and fade everything towards the top and bottom edges
                edge = min(1.0, (r + 0.5) / 3, (rows - r - 0.5) / 3)
                level = round(LEVELS * (1 - k / (tail + 1)) * max(edge, 0))
                if level <= 0:
                    continue
                color = 3 if k == 0 and edge >= 1 else 3 + level
                ch = "1" if bits[c][r] >> (f // 3) & 1 else "0"  # glyphs flicker every 3 frames
                d.text((x0 + c * CELL_W + CELL_W / 2, r * CELL_H + CELL_H / 2), ch,
                       fill=color, font=font, anchor="mm")
        d.rounded_rectangle((0, 0, W - 1, H - 1), radius=10, outline=2)
        im.paste(0, mask=Image.eval(mask, lambda v: 255 - v))
        frames.append(im)

    path.parent.mkdir(parents=True, exist_ok=True)
    frames[0].save(path, save_all=True, append_images=frames[1:], duration=FRAME_MS, loop=0,
                   transparency=0, disposal=1, optimize=False)


if __name__ == "__main__":
    render(Path(__file__).resolve().parent.parent / "assets" / "rain.gif")
