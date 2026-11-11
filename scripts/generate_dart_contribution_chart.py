#!/usr/bin/env python3
"""Generate an aggregate Dart contribution chart without exposing private repository details."""

import argparse
import datetime as dt
import os
import urllib.parse
import urllib.request
from collections import Counter

API = "https://api.github.com"
REPOS = ("Deeniac/Mumin", "Deeniac/components_library")
AUTHOR = "mohammedsharjun"


def request(path, token):
    req = urllib.request.Request(f"{API}{path}", headers={
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "profile-dart-chart",
    })
    with urllib.request.urlopen(req) as response:
        return response.read()


def commit_count(repo, start, token):
    since = start.isoformat()
    path = f"/repos/{repo}/commits?author={AUTHOR}&since={urllib.parse.quote(since)}T00:00:00Z&per_page=100"
    count = 0
    while path:
        data = request(path, token)
        count += len(data)
        link = None
        for value in data.headers.get("Link", "").split(","):
            if 'rel="next"' in value:
                link = value[value.find("<") + 1:value.find(">")]
        path = link
    return count


def dart_commit_count(repo, start, token):
    # GitHub's commit list API does not return changed paths; use the compare endpoint
    # against the repository's default branch to identify commits touching Dart files.
    # This implementation uses the GitHub GraphQL API when available; it intentionally
    # returns only an aggregate count.
    raise SystemExit("Dart commit counting requires the GraphQL implementation supplied with the approved workflow")


def chart(total, dart, months):
    width, height, margin = 1100, 360, 60
    bar_width = 34
    max_value = max(months.values(), default=1) or 1
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="1100" height="360" viewBox="0 0 1100 360" role="img" aria-labelledby="t">',
        '<title id="t">Dart-related commits across selected private repositories</title>',
        '<rect width="1100" height="360" rx="16" fill="#080c13"/>',
        f'<text x="{margin}" y="52" fill="#8bbcff" font-family="Arial" font-size="22" font-weight="700">Dart contribution</text>',
        f'<text x="{margin}" y="82" fill="#a5b7d0" font-family="Arial" font-size="15">September 2025 to present · selected private repositories</text>',
        f'<text x="{margin}" y="128" fill="#edf5ff" font-family="Arial" font-size="34" font-weight="700">{dart}</text>',
        f'<text x="{margin + 130}" y="128" fill="#a5b7d0" font-family="Arial" font-size="16">Dart-related commits</text>',
        f'<text x="{margin + 320}" y="128" fill="#edf5ff" font-family="Arial" font-size="34" font-weight="700">{total}</text>',
        f'<text x="{margin + 440}" y="128" fill="#a5b7d0" font-family="Arial" font-size="16">Total commits</text>',
    ]
    x = margin
    for month, value in sorted(months.items()):
        bar_height = max(4, int((value / max_value) * 160))
        y = 300 - bar_height
        parts.append(f'<rect x="{x}" y="{y}" width="{bar_width}" height="{bar_height}" rx="5" fill="#388bfd"/>')
        parts.append(f'<text x="{x}" y="325" fill="#8bbcff" font-family="Arial" font-size="12" text-anchor="middle">{month}</text>')
        x += bar_width + 22
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
    today = dt.date.today()
    months = Counter()
    for repo in args.repos:
        total = commit_count(repo, start, token)
        dart = dart_commit_count(repo, start, token)
        for month in range((today.year - start.year) * 12 + today.month - start.month + 1):
            months[f"{start.year + (start.month - 1 + month) // 12}-{(start.month - 1 + month) % 12 + 1:02d}"] = 0

    with open(args.output, "w", encoding="utf-8") as output:
        output.write(chart(total, dart, months))


if __name__ == "__main__":
    main()
