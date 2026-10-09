# Profile generator

`README.md` at the repo root is generated: edit `profile.toml`, not the README.

Everything readable is plain text in code blocks, which github.com draws itself, so
the profile looks the same in every browser, theme and screen size, in the GitHub
mobile apps, with screen readers, and on networks that block GitHub's image servers
(`*.githubusercontent.com`). The two images (rain banner, visitor counter) are
decorative with `alt=""`, so if they can't load they disappear instead of leaving
broken links. Code-block lines are capped at 36 ASCII characters so they fit a phone
screen; the build stops with a clear message if a line in `profile.toml` is too long.

| file | what it does |
| --- | --- |
| `../profile.toml` | the content: boot log, profile rows, focus, spoken languages, stack |
| `build.py` | entry point; `--fetch` refreshes GitHub stats into `../data/github.json` |
| `readme.py` | renders `README.md` as terminal transcripts |
| `stats.py` | GitHub stats + contribution calendar, via the GraphQL API |
| `banner.py` | the looping binary rain GIF (`../assets/rain.gif`) |
| `fonts/` | VT323 for the rain glyphs (SIL OFL 1.1, see `OFL.txt`) |

```sh
pip install -r scripts/requirements.txt
python scripts/build.py                                   # rebuild from cached stats
GITHUB_TOKEN=ghp_xxx python scripts/build.py --fetch      # also refresh stats
```

The `matrix-sync` workflow runs this every day and on every push that touches
`profile.toml` or `scripts/`, then commits the updated README.
