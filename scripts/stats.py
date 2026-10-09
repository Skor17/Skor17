"""GitHub stats straight from the GraphQL API (no third-party stats services that can
rate-limit or go down). fetch() returns the snapshot cached in data/github.json;
readme.py turns it into text.
"""

from __future__ import annotations

import datetime as dt

import requests

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
