#!/usr/bin/env python3
"""Generate an aggregate Dart contribution chart from selected private repositories."""

import argparse
import datetime as dt
import json
import os
import urllib.request
from collections import Counter

API = "https://api.github.com/graphql"
AUTHOR = "mohammedsharjun"

QUERY = """
query($owner: String!, $name: String!, $since: DateTime!, $after: String) {
  repository(owner: $owner, name: $name) {
    defaultBranchRef {
      target {
        ... on Commit {
          history(first: 100, since: $since, author: {login: $author}, after: $after) {
            pageInfo { hasNextPage endCursor }
            totalCount
            nodes {
              committedDate
              files(first: 100) {
                pageInfo { hasNextPage }
                nodes { path }
              }
            }
          }
        }
      }
    }
  }
}
"""


def graphql(query, variables, token):
    payload = json.dumps({"query": query, "variables": variables}).encode()
    request = urllib.request.Request(API, data=payload, headers={
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "User-Agent": "profile-dart-chart",
    })
    with urllib.request.urlopen(request) as response:
        result = json.load(response)
    if result.get("errors"):
        raise SystemExit(f"GitHub GraphQL error: {result['errors']}")
    return result["data"]


def repository_stats(repo, start, token):
    owner, name = repo.split("/", 1)
    cursor = None
    total = 0
    dart = 0
    months = Counter()
    while True:
        data = graphql(QUERY, {
            "owner": owner,
            "name": name,
            "since": f"{start.isoformat()}T00:00:00Z",
            "after": cursor,
            "author": AUTHOR,
        }, token)
        history = data["repository"]["defaultBranchRef"]["target"]["history"]
        total += len(history["nodes"])
        for commit in history["nodes"]:
            date = dt.datetime.fromisoformat(commit["committedDate"].replace("Z", "+00:00")).date()
            month = f"{date.year}-{date.month:02d}"
            is_dart = any(node["path"].endswith(".dart") for node in commit["files"]["nodes"])
            if is_dart:
                dart += 1
                months[month] += 1
        if not history["pageInfo"]["hasNextPage"]:
            break
        cursor = history["pageInfo"]["endCursor"]
    return total, dart, months


def fill_months(start, months):
    today = dt.date.today()
    current = dt.date(start.year, start.month, 1)
    while current <= today:
        months.setdefault(f"{current.year}-{current.month:02d}", 0)
        current = dt.date(current.year + (current.month == 12), (current.month % 12) + 1, 1)
    return months


def chart(total, dart, months):
    margin, bar_width = 60, 30
    max_value = max(months.values(), default=1) or 1
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="1100" height="360" viewBox="0 0 1100 360" role="img" aria-labelledby="t">',
        '<title id="t">Dart-related commits across selected private repositories</title>',
        '<rect width="1100" height="360" rx="16" fill="#080c13"/>',
        '<text x="60" y="52" fill="#8bbcff" font-family="Arial" font-size="22" font-weight="700">Dart contribution</text>',
        '<text x="60" y="82" fill="#a5b7d0" font-family="Arial" font-size="15">September 2025 to present · selected private repositories</text>',
        f'<text x="60" y="130" fill="#edf5ff" font-family="Arial" font-size="34" font-weight="700">{dart}</text>',
        '<text x="190" y="130" fill="#a5b7d0" font-family="Arial" font-size="16">Dart-related commits</text>',
        f'<text x="380" y="130" fill="#edf5ff" font-family="Arial" font-size="34" font-weight="700">{total}</text>',
        '<text x="500" y="130" fill="#a5b7d0" font-family="Arial" font-size="16">Total commits</text>',
    ]
    x = margin
    for month, value in sorted(months.items()):
        bar_height = max(4, round(value / max_value * 150))
        y = 300 - bar_height
        parts.append(f'<rect x="{x}" y="{y}" width="{bar_width}" height="{bar_height}" rx="5" fill="#388bfd"/>')
        parts.append(f'<text x="{x + bar_width / 2}" y="325" fill="#8bbcff" font-family="Arial" font-size="11" text-anchor="middle">{month[5:]}</text>')
        x += bar_width + 18
    parts.append("</svg>")
    return "\n".join(parts)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--start-date", required=True)
    parser.add_argument("--repos", nargs="+", required=True)
    args = parser.parse_args()

    token = os.environ.get("PRIVATE_REPO_READ_TOKEN")
    if not token:
        raise SystemExit("PRIVATE_REPO_READ_TOKEN is not available")

    start = dt.date.fromisoformat(args.start_date)
    total = 0
    dart = 0
    months = Counter()
    for repo in args.repos:
        repo_total, repo_dart, repo_months = repository_stats(repo, start, token)
        total += repo_total
        dart += repo_dart
        months.update(repo_months)

    months = fill_months(start, months)
    with open(args.output, "w", encoding="utf-8") as output:
        output.write(chart(total, dart, months))


if __name__ == "__main__":
    main()
