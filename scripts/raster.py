"""Turn the SVG cards into PNGs with headless Chromium.

PNG is the one image format every GitHub client shows the same way: browsers,
Safari/iOS, and the GitHub mobile apps. Each card is frozen at a moment where
everything is fully drawn (boot log typed out, cursors on), so the still frame
looks finished.
"""

from __future__ import annotations

import io
import os
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright

# seconds into the animations at which each card is captured (default: DEFAULT_T)
FREEZE_AT = {"boot": 10.7}
DEFAULT_T = 8.5

FREEZE_JS = """(t) => {
  for (const a of document.getAnimations()) {
    a.pause();
    // cursors are captured "on" and stack chips unlit; everything else at t seconds in
    a.currentTime = ["blink", "chip"].includes(a.animationName) ? 0 : t * 1000;
  }
  // moving scanners only make sense in motion: hide them in a still frame
  const st = document.createElementNS("http://www.w3.org/2000/svg", "style");
  st.textContent = ".sweep,.beam{display:none}";
  document.documentElement.appendChild(st);
  const r = document.documentElement.getBoundingClientRect();
  return [Math.ceil(r.width), Math.ceil(r.height)];
}"""


def rasterize(jobs: list[tuple[Path, Path, float]]) -> None:
    """jobs: (svg path, png path, device scale factor)."""
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=os.environ.get("CHROMIUM_PATH") or None)
        for svg, png, scale in jobs:
            page = browser.new_page(device_scale_factor=scale, viewport={"width": 1200, "height": 1200},
                                    reduced_motion="no-preference")
            page.goto(svg.resolve().as_uri())
            w, h = page.evaluate(FREEZE_JS, FREEZE_AT.get(svg.stem, DEFAULT_T))
            shot = page.screenshot(clip={"x": 0, "y": 0, "width": w, "height": h}, omit_background=True)
            page.close()
            # palette PNG: a fraction of the size, no visible difference on these green-on-black cards
            img = Image.open(io.BytesIO(shot)).quantize(256, method=Image.Quantize.FASTOCTREE, dither=Image.Dither.NONE)
            png.parent.mkdir(parents=True, exist_ok=True)
            img.save(png, optimize=True)
        browser.close()
