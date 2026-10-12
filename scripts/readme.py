"""Render README.md as plain text: terminal transcripts in code blocks.

Everything that carries information is text that github.com draws itself, so the
profile reads the same in every browser, theme, screen reader, the GitHub mobile
apps, and on networks that block GitHub's image servers. The only images are
decorative (alt="") and simply vanish if they can't load.
"""

from __future__ import annotations

import datetime as dt
import math

import pyfiglet

from stats import fmt, streaks

# Widest line allowed in a code block. Code blocks don't wrap, and ~36 monospace
# characters is what fits on a small phone (360px) without sideways scrolling.
MAX = 36
RAW = "https://raw.githubusercontent.com/{login}/{login}/main"
HEAT = ".:+#@"  # 0 contributions .. busiest days
HEAT_WEEKS = 26


def leader(label: str, value: str, width: int = MAX) -> str:
    """'LABEL ........ value' padded to exactly `width` columns."""
    dots = width - len(label) - len(value) - 2
    return f"{label} {'.' * max(dots, 1)} {value}"


def wrap(words: list[str], width: int = MAX, sep: str = "  ") -> list[str]:
    lines, cur = [], ""
    for w in words:
        if cur and len(cur) + len(sep) + len(w) > width:
            lines.append(cur)
            cur = w
        else:
            cur = f"{cur}{sep}{w}" if cur else w
    return lines + [cur] if cur else lines


def prompt(p: dict, cmd: str) -> str:
    return f'{p["identity"]["handle"].lower()}@zion:~$ {cmd}'


def block(lines: list[str]) -> str:
    for line in lines:
        if len(line) > MAX:
            raise ValueError(f"line is {len(line)} chars, max {MAX} (shorten it in profile.toml): {line!r}")
        if not line.isascii():
            raise ValueError(f"non-ASCII text can misalign or show as boxes on some devices: {line!r}")
    # plain text: no syntax highlighter to recolour parts of it unpredictably
    return "```text\n" + "\n".join(lines) + "\n```"


# ── sections ─────────────────────────────────────────────────────────────────
def boot(p: dict) -> list[str]:
    logo = pyfiglet.figlet_format(p["identity"]["handle"], font="slant", width=200)
    lines = [l.rstrip() for l in logo.splitlines() if l.strip()]
    lines.append("")
    for msg, status in p["boot"]:
        if status:
            lines.append(leader(f"> {msg}", f"[ {status} ]", MAX - 2))
        else:
            lines.append(f"> {msg}...")
    lines.append("> ACCESS GRANTED_")
    return lines


def whoami(p: dict) -> list[str]:
    key_w = max(len(k) for k, _ in p["profile"]) + 2
    lines = [prompt(p, "whoami")]
    lines += [f"{k.ljust(key_w)}{v}" for k, v in p["profile"]]
    lines += ["", prompt(p, "cat focus.txt")]
    lines += [f"[*] {f}" for f in p["focus"]]
    lines += ["", prompt(p, "locale --human")]
    lines += [f"{code}  {name}" for name, code in p["spoken"]]
    return lines


def arsenal(p: dict) -> list[str]:
    lines = [prompt(p, "ls ~/arsenal")]
    for cat, items in p["stack"].items():
        lines.append(f"// {cat}")
        lines += ["  " + line for line in wrap(items, MAX - 2)]
    return lines


def netstat(p: dict, data: dict | None, today: dt.date) -> list[str]:
    lines = [prompt(p, "netstat --github")]
    if not data:
        return lines + ["AWAITING UPLINK...", "(the matrix-sync workflow fills", " this in on its first run)"]
    rows = [("STARS EARNED", data["stars"]), ("COMMITS", data["commits"]),
            ("PULL REQUESTS", data["prs"]), ("ISSUES", data["issues"]),
            ("REPOSITORIES", data["repos"]), ("CONTRIBUTED TO", data["contributed_to"])]
    lines += [leader(k, fmt(v)) for k, v in rows]

    langs = sorted(data["languages"].items(), key=lambda kv: -kv[1])[:6]
    if langs:
        lines += ["", prompt(p, "top --languages")]
        total = sum(data["languages"].values())
        top = langs[0][1]
        for name, size in langs:
            cells = min(10, max(1, round(10 * size / top)))
            pct = f"{100 * size / total:.1f}%"
            lines.append(f"{name[:11].ljust(12)}[{'#' * cells}{'.' * (10 - cells)}] {pct.rjust(6)}")

    lines += ["", prompt(p, "cat contrib.log")]
    lines += heatmap(data)
    total, cur, longest, best = streaks(data["days"], today)
    lines += [
        leader("CONTRIBUTIONS (ALL TIME)", fmt(total)),
        leader("LAST 12 MONTHS", fmt(data["year_total"])),
        leader("CURRENT STREAK", f"{cur}d"),
        leader("LONGEST STREAK", f"{longest}d"),
        leader("BEST DAY", best),
        "",
        f"# last sync {data['synced']} (UTC)",
    ]
    return lines


def heatmap(data: dict) -> list[str]:
    """Last HEAT_WEEKS weeks of the contribution calendar, one column per week."""
    first = dt.date.fromisoformat(data["first_day"])
    weeks = data["weeks"]
    start = max(0, len(weeks) - HEAT_WEEKS)
    shown = weeks[start:]
    busiest = max((c or 0 for w in shown for c in w), default=0) or 1

    # month labels above the first week (Sunday) of each month
    head = [" "] * (4 + len(shown))
    last_end = 0
    for i in range(len(shown)):
        sunday = first + dt.timedelta(weeks=start + i)
        prev = sunday - dt.timedelta(weeks=1)
        col = 4 + i
        if sunday.month != prev.month and col >= last_end and col + 3 <= len(head):
            head[col:col + 3] = sunday.strftime("%b").upper()
            last_end = col + 4
    lines = ["".join(head).rstrip()]

    for d, label in enumerate(("Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat")):
        row = []
        for w in shown:
            c = w[d] if d < len(w) else None
            row.append(" " if c is None else HEAT[min(4, math.ceil(4 * c / busiest))])
        lines.append(f"{label} {''.join(row)}".rstrip())
    lines.append(f"    less {' '.join(HEAT)} more")
    return lines


def motto(p: dict) -> list[str]:
    return [prompt(p, "echo $MOTTO"), p["identity"]["motto"], prompt(p, "logout"), "[ connection closed ]"]


# ── page ─────────────────────────────────────────────────────────────────────
def render(p: dict, data: dict | None, login: str, today: dt.date | None = None) -> str:
    today = today or dt.date.today()
    raw = RAW.format(login=login)
    parts = [
        "<!--\n"
        "  GENERATED FILE: edit profile.toml (and scripts/), not this README.\n"
        "  The matrix-sync workflow rebuilds it and refreshes the stats every day.\n"
        "\n"
        "  Everything readable is text inside code blocks, so it shows on every device,\n"
        "  browser, theme and network. Images are decoration only (alt=\"\"): if a network\n"
        "  blocks GitHub's image servers they vanish instead of leaving broken links.\n"
        "-->",
        f'<p align="center"><img src="{raw}/assets/rain.gif" width="100%" alt="" /></p>',
        block(boot(p)),
        block(whoami(p)),
        block(arsenal(p)),
        block(netstat(p, data, today)),
        block(motto(p)),
        f'<p align="center"><img src="https://komarev.com/ghpvc/?username={login}&style=flat-square'
        f'&color=05ff62&label=VISITORS&labelColor=0d1117" alt="" /></p>',
    ]
    return "\n\n".join(parts) + "\n"
