"""Build README.md (all text) and the decorative rain banner assets/rain.gif.

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
import readme  # noqa: E402
import stats  # noqa: E402

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

    (ROOT / "README.md").write_text(readme.render(profile, data, args.user), encoding="utf-8")
    print("built README.md")
    banner.render(ROOT / "assets" / "rain.gif")
    print("built assets/rain.gif")


if __name__ == "__main__":
    main()
