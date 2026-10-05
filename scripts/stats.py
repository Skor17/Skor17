"""Self-hosted GitHub stats cards (no third-party stats services that can rate-limit or go down).

fetch() talks to the GitHub GraphQL API; render_* draw the cards from the
cached JSON in data/github.json, or an "awaiting uplink" placeholder when no
data has been fetched yet.
"""

from __future__ import annotations

import datetime as dt
import math
import random

import requests

from svgkit import BG, CRT, DIM, GREEN, HOT, LINE, MID, MONO, PANEL, SVG, crt_defs, frame, overlay
from cards import NARROW, W, refresh_beam, section_title
API = "https://api.github.com/graphql"

PROFILE_Q = """
query($login: String!, $cursor: String) {
  user(login: $login) {
    login
    createdAt
    followers { totalCount }
    pullRequests { totalCount }
    issues { totalCount }
    repositoriesContributedTo(contributionTypes: [COMMIT, ISSUE, PULL_REQUEST, REPOSITORY]) { totalCount }
    repositories(first: 100, after: $cursor, ownerAffiliations: OWNER, isFork: false) {
      totalCount
      pageInfo { hasNextPage endCursor }
      nodes {
        stargazerCount
        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) { edges { size node { name } } }
      }
    }
  }
}"""

CAL_Q = """
query($login: String!, $from: DateTime, $to: DateTime) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      totalCommitContributions
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount } }
      }
    }
  }
}"""


def _gql(token: str, query: str, **variables) -> dict:
    r = requests.post(API, json={"query": query, "variables": variables},
                      headers={"Authorization": f"bearer {token}"}, timeout=30)
    r.raise_for_status()
    body = r.json()
    if body.get("errors"):
        raise RuntimeError(body["errors"])
    return body["data"]["user"]


def fetch(login: str, token: str) -> dict:
    stars, langs, cursor = 0, {}, None
    while True:
        u = _gql(token, PROFILE_Q, login=login, cursor=cursor)
        repos = u["repositories"]
        for node in repos["nodes"]:
            stars += node["stargazerCount"]
            for e in node["languages"]["edges"]:
                langs[e["node"]["name"]] = langs.get(e["node"]["name"], 0) + e["size"]
        if not repos["pageInfo"]["hasNextPage"]:
            break
        cursor = repos["pageInfo"]["endCursor"]

    now = dt.datetime.now(dt.timezone.utc)
    days: dict[str, int] = {}
    commits = 0
    for year in range(int(u["createdAt"][:4]), now.year + 1):
        start = dt.datetime(year, 1, 1, tzinfo=dt.timezone.utc)
        end = min(dt.datetime(year, 12, 31, 23, 59, 59, tzinfo=dt.timezone.utc), now)
        cc = _gql(token, CAL_Q, login=login, **{"from": start.isoformat(), "to": end.isoformat()})["contributionsCollection"]
        commits += cc["totalCommitContributions"]
        for w in cc["contributionCalendar"]["weeks"]:
            for d in w["contributionDays"]:
                days[d["date"]] = d["contributionCount"]

    # the default window is exactly what github.com shows on the profile
    last_year = _gql(token, CAL_Q, login=login)["contributionsCollection"]["contributionCalendar"]
    weeks = [[d["contributionCount"] for d in w["contributionDays"]] for w in last_year["weeks"]]
    # the first week can be partial: pad it so row 0 is always Sunday
    first = dt.date.fromisoformat(last_year["weeks"][0]["contributionDays"][0]["date"])
    pad = first.isoweekday() % 7
    weeks[0] = [None] * pad + weeks[0]
    first_day = (first - dt.timedelta(days=pad)).isoformat()

    return {
        "login": u["login"],
        "synced": now.strftime("%Y-%m-%d"),
        "stars": stars,
        "commits": commits,
        "prs": u["pullRequests"]["totalCount"],
        "issues": u["issues"]["totalCount"],
        "repos": repos["totalCount"],
        "contributed_to": u["repositoriesContributedTo"]["totalCount"],
        "followers": u["followers"]["totalCount"],
        "languages": dict(sorted(langs.items(), key=lambda kv: -kv[1])),
        "days": dict(sorted(days.items())),
        "year_total": last_year["totalContributions"],
        "weeks": weeks,
        "first_day": first_day,
    }


def streaks(days: dict[str, int], today: dt.date) -> tuple[int, int, int, str]:
    """(total, current streak, longest streak, best day) from a date -> count map."""
    total = sum(days.values())
    longest = run = 0
    prev = None
    for ds in sorted(days):
        d = dt.date.fromisoformat(ds)
        if d > today:
            break
        if days[ds] > 0:
            run = run + 1 if prev and (d - prev).days == 1 else 1
            prev = d
            longest = max(longest, run)
    current = 0
    d = today
    if days.get(d.isoformat(), 0) == 0:  # today not over yet: don't break the streak
        d -= dt.timedelta(days=1)
    while days.get(d.isoformat(), 0) > 0:
        current += 1
        d -= dt.timedelta(days=1)
    best = max(days.values(), default=0)
    return total, current, longest, str(best)


def fmt(n: int | None) -> str:
    if n is None:
        return "--"
    return f"{n / 1000:.1f}k" if n >= 10000 else f"{n:,}".replace(",", "'")


# ── netstat card ─────────────────────────────────────────────────────────────
def render_stats(data: dict | None, W: int = W) -> SVG:
    narrow = W <= NARROW
    lx, y0 = 28, 70
    lw = W - 2 * lx if narrow else 380
    # narrow: TOP LANGUAGES goes below GITHUB STATS instead of beside it
    rx, ry = (lx, y0 + 40 + 6 * 27 + 16) if narrow else (450, y0)
    H = ry + 204
    d = data or {}
    rows = [("STARS EARNED", d.get("stars")), ("COMMITS", d.get("commits")),
            ("PULL REQUESTS", d.get("prs")), ("ISSUES", d.get("issues")),
            ("REPOSITORIES", d.get("repos")), ("CONTRIBUTED TO", d.get("contributed_to"))]
    langs = list((d.get("languages") or {}).items())
    total = sum(v for _, v in langs) or 1
    top = [(n, v / total * 100) for n, v in langs[:6]]
    desc = "GITHUB STATS — " + ", ".join(f"{k}: {fmt(v)}" for k, v in rows)
    desc += ". TOP LANGUAGES — " + (", ".join(f"{n} {p:.1f}%" for n, p in top) or "awaiting first sync")
    svg = SVG(W, H, "GitHub stats", desc)
    crt_defs(svg)
    frame(svg, "skor17@zion: ~$ netstat --github", "SYNCED DAILY" if data else "NO SIGNAL")

    section_title(svg, "GITHUB STATS", lx, y0, lw)
    for i, (k, v) in enumerate(rows):
        y = y0 + 40 + i * 27
        svg.add(
            svg.text(k, lx, y, 15, MONO, DIM, spacing=1.5),
            f'<line x1="{lx + 150}" y1="{y - 4}" x2="{lx + lw - 62}" y2="{y - 4}" stroke="{LINE}" stroke-dasharray="1 5"/>',
            svg.text(fmt(v), lx + lw, y + 2, 26, CRT, HOT if data else DIM, "end", 1,
                     'filter="url(#glow)"' if data else ""),
        )

    rw = W - rx - 28
    section_title(svg, "TOP LANGUAGES", rx, ry, rw)
    svg.styles.append("@keyframes fill{from{transform:scaleX(0)}to{transform:scaleX(1)}}"
                      ".bar{transform-box:fill-box;transform-origin:left center;animation:fill 1.6s cubic-bezier(.2,.8,.2,1) both}")
    if top:
        bw = rw - 132 - 66
        for i, (name, pct) in enumerate(top):
            y = ry + 40 + i * 27
            svg.add(
                svg.text(name[:16], rx, y, 15, MONO, HOT),
                f'<rect x="{rx + 132}" y="{y - 11}" width="{bw}" height="12" fill="{PANEL}" stroke="{LINE}"/>',
                f'<rect class="bar" style="animation-delay:{i * 0.12:.2f}s" x="{rx + 134}" y="{y - 9}" '
                f'width="{max(2, (bw - 4) * pct / top[0][1]):.1f}" height="8" fill="{GREEN if i == 0 else MID}"/>',
                svg.text(f"{pct:.1f}%", rx + rw, y, 15, MONO, GREEN, "end"),
            )
    else:
        no_signal(svg, rx + rw / 2, ry + 105)
    overlay(svg)
    refresh_beam(svg)
    return svg


def no_signal(svg: SVG, cx: float, cy: float) -> None:
    svg.styles.append("@keyframes ns{0%,100%{opacity:1}50%{opacity:.3}}.ns{animation:ns 1.2s steps(2) infinite}")
    svg.add(
        '<g class="ns">' + svg.text("AWAITING UPLINK", cx, cy, 30, CRT, GREEN, "middle", 3, 'filter="url(#glow)"') + "</g>",
        svg.text("first sync runs via GitHub Actions", cx, cy + 26, 14, MONO, DIM, "middle", 0.5),
    )


# ── contribution heatmap + streaks ───────────────────────────────────────────
LEVELS = ["#0a2414", "#0f5a2c", "#1a9c4a", GREEN, HOT]


def render_activity(data: dict | None, today: dt.date | None = None, W: int = W) -> SVG:
    narrow = W <= NARROW
    shown = 27 if narrow else 53  # weeks of the heatmap that fit (incl. the current one)
    today = today or dt.date.today()
    if data:
        weeks = data["weeks"]
        first = dt.date.fromisoformat(data["first_day"])
        total, cur, longest, best = streaks(data["days"], today)
        year_total = data["year_total"]
    else:
        weeks, first = [[0] * 7 for _ in range(53)], today - dt.timedelta(days=52 * 7 + today.isoweekday() % 7)
        total = cur = longest = None
        best, year_total = None, None
    first += dt.timedelta(weeks=max(0, len(weeks) - shown))
    weeks = weeks[-shown:]
    figures = [("TOTAL CONTRIBUTIONS", fmt(total)), ("CURRENT STREAK", f"{cur}d" if cur is not None else "--"),
               ("LONGEST STREAK", f"{longest}d" if longest is not None else "--"), ("BEST DAY", best or "--")]
    # narrow: the four figures sit in a 2x2 grid
    per_row = 2 if narrow else 4
    H = 284 + (64 if narrow else 0)
    svg = SVG(W, H, "Contribution activity",
              f"Contribution heatmap for the last year ({fmt(year_total)} contributions). "
              + ", ".join(f"{k}: {v}" for k, v in figures))
    crt_defs(svg)
    frame(svg, f"skor17@zion: ~$ cat contrib.log --last {shown - 1}w",
          f"{fmt(year_total)} IN THE LAST YEAR" if data else "NO SIGNAL")

    cell, gap = (10, 3) if narrow else (11, 3)
    step = cell + gap
    gx = (W - len(weeks) * step + gap) / 2 + 12
    gy = 74
    mx = max((c or 0 for w in weeks for c in w), default=0) or 1
    rnd = random.Random(7)
    svg.styles.append("@keyframes tw{0%,100%{opacity:1}50%{opacity:.35}}.tw{animation:tw 2.2s ease-in-out infinite}")
    cells = []
    last_month = None
    for wi, week in enumerate(weeks):
        wd = first + dt.timedelta(days=wi * 7)
        if wd.month != last_month and wi < len(weeks) - 2:
            if last_month is not None or wd.day <= 7:
                cells.append(svg.text(wd.strftime("%b").upper(), gx + wi * step, gy - 8, 15, CRT, DIM, spacing=1))
            last_month = wd.month
        for di, c in enumerate(week):
            if c is None:  # padding before the first tracked day
                continue
            lvl = min(4, math.ceil(4 * c / mx)) if c else 0
            tw = f' class="tw" style="animation-delay:{-rnd.uniform(0, 2.2):.2f}s"' if c and rnd.random() < 0.18 else ""
            cells.append(f'<rect{tw} x="{gx + wi * step:.1f}" y="{gy + di * step}" width="{cell}" height="{cell}" rx="2" fill="{LEVELS[lvl]}"/>')
    for di, lbl in ((1, "MON"), (3, "WED"), (5, "FRI")):
        cells.append(svg.text(lbl, gx - 10, gy + di * step + 10, 14, CRT, DIM, "end", 1))
    svg.add(*cells)

    # scanner sweeping across the grid
    gw = len(weeks) * step
    svg.styles.append(f"@keyframes sweep{{from{{transform:translateX(0)}}to{{transform:translateX({gw:.0f}px)}}}}"
                      ".sweep{animation:sweep 6s linear infinite}")
    svg.defs.append('<linearGradient id="sw" x1="0" x2="1"><stop offset="0" stop-color="#05ff62" stop-opacity="0"/>'
                    '<stop offset="1" stop-color="#05ff62" stop-opacity=".35"/></linearGradient>')
    svg.add(f'<g transform="translate({gx - 30:.1f} 0)"><g class="sweep"><rect x="0" y="{gy - 4}" width="30" height="{7 * step + 4}" fill="url(#sw)"/>'
            f'<rect x="29" y="{gy - 4}" width="1.5" height="{7 * step + 4}" fill="{HOT}"/></g></g>')

    # legend
    lgx = W - 28 - 5 * 14 - 40
    ly = gy + 7 * step + 18
    svg.add(svg.text("LESS", lgx - 8, ly + 10, 14, CRT, DIM, "end", 1))
    for i, c in enumerate(LEVELS):
        svg.add(f'<rect x="{lgx + i * 14}" y="{ly}" width="11" height="11" rx="2" fill="{c}"/>')
    svg.add(svg.text("MORE", lgx + 5 * 14 + 6, ly + 10, 14, CRT, DIM, spacing=1))

    # figures
    fw = (W - 56) / per_row
    for i, (label, value) in enumerate(figures):
        x = 28 + i % per_row * fw
        fy = 246 + i // per_row * 64
        svg.add(
            f'<rect x="{x + 4:.1f}" y="{fy - 34}" width="{fw - 8:.1f}" height="56" rx="4" fill="{PANEL}" stroke="{LINE}"/>',
            svg.text(value, x + fw / 2, fy - 2, 28, CRT, HOT if data else DIM, "middle", 1,
                     'filter="url(#glow)"' if data else ""),
            svg.text(label, x + fw / 2, fy + 13, 11, MONO, DIM, "middle", 1.5),
        )
    if not data:
        svg.add(f'<rect x="{W / 2 - 170}" y="{gy + 20}" width="340" height="60" rx="4" fill="{BG}" fill-opacity=".85" stroke="{LINE}"/>')
        no_signal(svg, W / 2, gy + 50)
    overlay(svg)
    refresh_beam(svg)
    return svg
