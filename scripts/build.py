"""Build the image cards (assets/cards/*.png), the rain banner (assets/rain.gif) and README.md.

    python scripts/build.py            # rebuild from profile.toml + cached data/github.json
    GITHUB_TOKEN=... python scripts/build.py --fetch [--user Skor17]   # refresh GitHub stats first
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

import banner  # noqa: E402
import cards  # noqa: E402
import raster  # noqa: E402
import readme  # noqa: E402
import stats  # noqa: E402

ASSETS = ROOT / "assets"
CACHE = ROOT / "data" / "github.json"
# cards use the narrow (stacked) layout, which stays readable on a phone; 3x pixels
WIDTH, SCALE = cards.NARROW, 3


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
        except Exception as exc:  # keep the last good snapshot rather than publishing a broken README
            print(f"::warning::GitHub stats fetch failed, keeping cached data: {exc}")
        else:
            CACHE.parent.mkdir(exist_ok=True)
            CACHE.write_text(json.dumps(data, indent=1) + "\n", encoding="utf-8")
            print(f"fetched stats for {args.user}")
    if data is None and CACHE.exists():
        data = json.loads(CACHE.read_text(encoding="utf-8"))
    if data is None:
        print("no GitHub stats yet: the README shows a placeholder")

    # render the README first: it validates profile.toml (line widths, ASCII)
    text = readme.render(profile, data, args.user)

    svgs = {name: build(profile, W=WIDTH) for name, build in cards.STATIC_CARDS.items()}
    svgs["stats"] = stats.render_stats(data, W=WIDTH)
    svgs["activity"] = stats.render_activity(data, W=WIDTH)
    jobs = []
    for name, svg in svgs.items():
        src = ASSETS / "_svg" / f"{name}.svg"  # git-ignored intermediate
        svg.save(src)
        jobs.append((src, ASSETS / "cards" / f"{name}.png", SCALE))
    raster.rasterize(jobs)
    for _, png, _ in jobs:
        print(f"built {png.relative_to(ROOT)}")
    banner.render(ASSETS / "rain.gif")
    print("built assets/rain.gif")

    missing = [c for c in readme.CARDS if not (ASSETS / "cards" / f"{c}.png").exists()]
    if missing:
        sys.exit(f"README references cards that were not built: {missing}")
    (ROOT / "README.md").write_text(text, encoding="utf-8")
    print("built README.md")


if __name__ == "__main__":
    main()
