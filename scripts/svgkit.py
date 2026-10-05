"""Tiny SVG toolkit for the profile cards.

Every piece of text is drawn as vector outlines (glyph paths extracted from the
fonts in ./fonts), so the cards look identical on every OS, browser and the
GitHub mobile app: no web fonts to load, no fallback fonts, no tofu boxes.
"""

from __future__ import annotations

import html
from functools import lru_cache
from pathlib import Path

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont

FONT_DIR = Path(__file__).parent / "fonts"

# ── palette ──────────────────────────────────────────────────────────────────
BG = "#020a04"        # near-black with a green cast (CRT glass)
PANEL = "#04130a"
LINE = "#0f3d1f"      # dim phosphor for borders and rules
DIM = "#1d7a3f"
MID = "#22c55e"
GREEN = "#05ff62"     # the brand green from the original README
HOT = "#b8ffd0"       # "head" of a falling glyph / highlights
AMBER = "#ffb000"     # 80s amber monitor accent
MAGENTA = "#ff2bd6"   # glitch split channels
CYAN = "#00e5ff"


class Font:
    def __init__(self, filename: str, key: str):
        self.key = key
        self.tt = TTFont(FONT_DIR / filename)
        self.upm = self.tt["head"].unitsPerEm
        self.cmap = self.tt.getBestCmap()
        self.glyphs = self.tt.getGlyphSet()
        self.hmtx = self.tt["hmtx"]

    def gname(self, ch: str) -> str:
        return self.cmap.get(ord(ch)) or self.cmap[ord("?")]

    def advance(self, ch: str) -> int:
        return self.hmtx[self.gname(ch)][0]

    def width(self, s: str, size: float, spacing: float = 0) -> float:
        return sum(self.advance(c) for c in s) * size / self.upm + spacing * max(len(s) - 1, 0)

    @lru_cache(maxsize=None)
    def path(self, ch: str) -> str:
        pen = SVGPathPen(self.glyphs, ntos=lambda v: f"{v:.0f}")
        # flip Y here so <use> needs only a uniform scale
        self.glyphs[self.gname(ch)].draw(TransformPen(pen, (1, 0, 0, -1, 0, 0)))
        return pen.getCommands()


DISPLAY = Font("Orbitron-Black.woff2", "o")   # big retro-futuristic headings
MONO = Font("ShareTechMono-Regular.woff2", "m")  # body / terminal text
CRT = Font("VT323-Regular.woff2", "v")         # pixel CRT accents + rain


class SVG:
    """Collects glyph <defs> and body markup for one card."""

    def __init__(self, width: int, height: int, title: str, desc: str = ""):
        self.w, self.h = width, height
        self.title, self.desc = title, desc
        self.glyph_defs: dict[str, str] = {}
        self.defs: list[str] = []
        self.styles: list[str] = []
        self.body: list[str] = []

    # -- text -----------------------------------------------------------------
    def _gid(self, font: Font, ch: str) -> str | None:
        if ch == " ":
            return None
        gid = f"{font.key}{ord(ch):x}"
        if gid not in self.glyph_defs:
            d = font.path(ch)
            if not d:
                return None
            self.glyph_defs[gid] = f'<path id="{gid}" d="{d}"/>'
        return gid

    def text(self, s: str, x: float, y: float, size: float, font: Font = MONO,
             fill: str | None = GREEN, anchor: str = "start", spacing: float = 0,
             attrs: str = "", mirror_every: int = 0) -> str:
        """Return markup for `s` with its baseline at (x, y).

        spacing is extra letter-spacing in px. mirror_every=n mirrors every
        n-th glyph horizontally (used by the digital rain).
        """
        k = size / font.upm
        w = font.width(s, size, spacing)
        if anchor == "middle":
            x -= w / 2
        elif anchor == "end":
            x -= w
        uses, cx = [], 0.0
        sp_units = spacing / k
        for i, ch in enumerate(s):
            gid = self._gid(font, ch)
            adv = font.advance(ch)
            if gid:
                if mirror_every and i % mirror_every == 0:
                    uses.append(f'<use xlink:href="#{gid}" transform="translate({cx + adv:.0f} 0) scale(-1 1)"/>')
                else:
                    uses.append(f'<use xlink:href="#{gid}" x="{cx:.0f}"/>')
            cx += adv + sp_units
        fill_attr = f' fill="{fill}"' if fill else ""
        return (f'<g transform="translate({x:.1f} {y:.1f}) scale({k:.5f})"{fill_attr} {attrs}>'
                + "".join(uses) + "</g>")

    def column(self, s: str, x: float, y: float, size: float, line: float, font: Font = CRT,
               fills: list[str] | None = None, opacities: list[float] | None = None) -> str:
        """Vertical stack of glyphs (centre-aligned on x), top baseline at y."""
        k = size / font.upm
        parts = []
        for i, ch in enumerate(s):
            gid = self._gid(font, ch)
            if not gid:
                continue
            adv = font.advance(ch)
            fx = f' fill="{fills[i]}"' if fills else ""
            op = f' opacity="{opacities[i]:.2f}"' if opacities else ""
            mirror = i % 3 == 1
            tx = (adv / 2) if mirror else (-adv / 2)
            sc = "scale(-1 1)" if mirror else ""
            parts.append(f'<use xlink:href="#{gid}" transform="translate({tx:.0f} {i * line / k:.0f}) {sc}"{fx}{op}/>')
        return f'<g transform="translate({x:.1f} {y:.1f}) scale({k:.5f})">' + "".join(parts) + "</g>"

    # -- output ---------------------------------------------------------------
    def add(self, *markup: str) -> None:
        self.body.extend(markup)

    def render(self) -> str:
        style = "\n".join(self.styles)
        reduced = "@media (prefers-reduced-motion: reduce){*{animation:none!important}}"
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
            f'width="{self.w}" height="{self.h}" viewBox="0 0 {self.w} {self.h}" role="img" '
            f'aria-labelledby="t d">'
            f'<title id="t">{html.escape(self.title)}</title>'
            f'<desc id="d">{html.escape(self.desc or self.title)}</desc>'
            f"<style>{style}\n{reduced}</style>"
            f'<defs>{"".join(self.glyph_defs.values())}{"".join(self.defs)}</defs>'
            + "".join(self.body)
            + "</svg>"
        )

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.render(), encoding="utf-8")


# ── shared card chrome ───────────────────────────────────────────────────────
def crt_defs(svg: SVG, uid: str = "") -> None:
    """Scanlines, vignette and glow filter shared by all cards."""
    svg.defs.append(
        f'<pattern id="scan{uid}" width="4" height="4" patternUnits="userSpaceOnUse">'
        f'<rect width="4" height="2" fill="#000" opacity=".28"/></pattern>'
        f'<radialGradient id="vig{uid}" cx="50%" cy="50%" r="75%">'
        f'<stop offset="60%" stop-color="#000" stop-opacity="0"/>'
        f'<stop offset="100%" stop-color="#000" stop-opacity=".65"/></radialGradient>'
        f'<filter id="glow{uid}" x="-20%" y="-20%" width="140%" height="140%">'
        f'<feGaussianBlur stdDeviation="2.2" result="b"/>'
        f'<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>'
    )


def frame(svg: SVG, label: str, right: str = "", uid: str = "") -> None:
    """Rounded terminal window with a title bar."""
    w, h = svg.w, svg.h
    svg.add(
        f'<rect x=".5" y=".5" width="{w - 1}" height="{h - 1}" rx="10" fill="{BG}" stroke="{LINE}"/>',
        f'<path d="M1 34 V10 A9 9 0 0 1 10 1 H{w - 10} A9 9 0 0 1 {w - 1} 10 V34 Z" fill="{PANEL}"/>',
        f'<path d="M1 34.5 H{w - 1}" stroke="{LINE}"/>',
    )
    for i, c in enumerate(("#ff5f56", AMBER, GREEN)):
        svg.add(f'<circle cx="{20 + i * 18}" cy="17.5" r="5" fill="none" stroke="{c}" stroke-width="1.5" opacity=".85"/>')
    svg.add(svg.text(label, 84, 23, 14, MONO, GREEN, spacing=1.5))
    if right:
        svg.add(svg.text(right, w - 18, 23, 14, MONO, DIM, anchor="end", spacing=1))


def overlay(svg: SVG, uid: str = "") -> None:
    """CRT scanlines + vignette on top of everything, clipped to the frame."""
    svg.add(
        f'<rect x="1" y="1" width="{svg.w - 2}" height="{svg.h - 2}" rx="9" fill="url(#scan{uid})" pointer-events="none"/>',
        f'<rect x="1" y="1" width="{svg.w - 2}" height="{svg.h - 2}" rx="9" fill="url(#vig{uid})" pointer-events="none"/>',
    )
