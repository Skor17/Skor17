"""Build every profile card as a PNG in assets/desktop/ and assets/mobile/.

    python scripts/build.py            # rebuild from profile.toml + cached data/github.json
    GITHUB_TOKEN=... python scripts/build.py --fetch [--user Skor17]   # refresh GitHub stats first

Cards are drawn as SVG (kept in assets/_svg/, git-ignored) and then rasterized:
PNG displays identically in every browser and in the GitHub mobile apps.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).parent))

import cards  # noqa: E402
import raster  # noqa: E402
import stats  # noqa: E402

ASSETS = ROOT / "assets"
# (folder, card width, pixel density): desktop browsers, and a stacked layout for phones
VARIANTS = (("desktop", cards.W, 2), ("mobile", cards.NARROW, 3))
CACHE = ROOT / "data" / "github.json"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fetch", action="store_true", help="refresh stats from the GitHub API")
    ap.add_argument("--user", default=os.environ.get("GITHUB_USER", "Skor17"))
    args = ap.parse_args()

    profile = tomllib.loads((ROOT / "profile.toml").read_text(encoding="utf-8"))

    data = None
    if args.fetch:
        token = os.environ.get("GITHUB_TOKEN")
        if not token:
            sys.exit("--fetch needs GITHUB_TOKEN")
        try:
            data = stats.fetch(args.user, token)
        except Exception as exc:  # keep the last good snapshot rather than publishing a broken card
            print(f"::warning::GitHub stats fetch failed, keeping cached data: {exc}")
        else:
            CACHE.parent.mkdir(exist_ok=True)
            CACHE.write_text(json.dumps(data, indent=1) + "\n", encoding="utf-8")
            print(f"fetched stats for {args.user}")
    if data is None and CACHE.exists():
        data = json.loads(CACHE.read_text(encoding="utf-8"))

    if data is None:
        print("no GitHub stats yet: stats cards show a placeholder")

    jobs = []
    for variant, width, scale in VARIANTS:
        svgs = {name: build(profile, W=width) for name, build in cards.STATIC_CARDS.items()}
        svgs["stats"] = stats.render_stats(data, W=width)
        svgs["activity"] = stats.render_activity(data, W=width)
        for name, svg in svgs.items():
            src = ASSETS / "_svg" / variant / f"{name}.svg"
            svg.save(src)
            jobs.append((src, ASSETS / variant / f"{name}.png", scale))
    raster.rasterize(jobs)
    for _, png, _ in jobs:
        print(f"built {png.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
