# Card generator

All images in `assets/` are generated, do not edit them by hand. Each card is drawn as
SVG and rendered to `assets/cards/*.png` (440px layout, 3x pixels) because PNG
displays the same everywhere, including the GitHub mobile apps. `assets/rain.gif`
is the text-free binary rain banner.

| file | what it does |
| --- | --- |
| `../profile.toml` | the content: name, profile rows, focus, spoken languages, stack |
| `build.py` | entry point; `--fetch` refreshes GitHub stats into `../data/github.json` |
| `raster.py` | renders the SVGs to PNG with headless Chromium (Playwright) |
| `banner.py` | the looping binary rain GIF |
| `cards.py` | static cards (header, boot log, whoami, languages/monitor, stack, footer) |
| `stats.py` | GitHub stats + contribution heatmap, via the GraphQL API |
| `svgkit.py` | turns text into glyph outlines so cards render identically everywhere |
| `fonts/` | Orbitron, Share Tech Mono, VT323 (SIL OFL 1.1, see `OFL.txt`) |

```sh
pip install -r scripts/requirements.txt
python -m playwright install chromium
python scripts/build.py                                   # rebuild from cached stats
GITHUB_TOKEN=ghp_xxx python scripts/build.py --fetch      # also refresh stats
```

The `matrix-sync` workflow runs this every day and on every push that touches
`profile.toml` or `scripts/`, then commits the updated PNGs.
