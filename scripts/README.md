# Profile generator

`README.md` at the repo root is generated: edit `profile.toml`, not the README.

The profile is the image cards (`assets/cards/*.png`, drawn as SVG and rendered to
PNG with headless Chromium) plus a collapsible **TEXT MODE** section with the same
content as plain text. The images have `alt=""`, so on networks that block GitHub's
image servers (`*.githubusercontent.com`) they disappear instead of leaving broken
links, and TEXT MODE still shows everything (also for screen readers). Text lines are
capped at 36 ASCII characters so they fit a phone screen; the build stops with a
clear message if a line in `profile.toml` is too long.

| file | what it does |
| --- | --- |
| `../profile.toml` | the content: boot log, profile rows, focus, spoken languages, stack |
| `build.py` | entry point; `--fetch` refreshes GitHub stats into `../data/github.json` |
| `readme.py` | renders `README.md`: the cards plus the TEXT MODE transcripts |
| `cards.py` | static cards (header, boot log, whoami, languages/monitor, stack, footer) |
| `raster.py` | renders the SVG cards to PNG with headless Chromium (Playwright) |
| `svgkit.py` | turns text into glyph outlines so cards render identically everywhere |
| `stats.py` | GitHub stats + contribution heatmap, via the GraphQL API |
| `banner.py` | the looping binary rain GIF (`../assets/rain.gif`) |
| `fonts/` | Orbitron, Share Tech Mono, VT323 (SIL OFL 1.1, see `OFL.txt`) |

```sh
pip install -r scripts/requirements.txt
python -m playwright install chromium
python scripts/build.py                                   # rebuild from cached stats
GITHUB_TOKEN=ghp_xxx python scripts/build.py --fetch      # also refresh stats
```

The `matrix-sync` workflow runs this every day and on every push that touches
`profile.toml` or `scripts/`, then commits the updated README and cards.
