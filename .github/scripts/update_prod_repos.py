#!/usr/bin/env python3
"""
update_prod_repos.py
--------------------
Queries the GitHub API for all public repositories owned by GITHUB_USER that
have a non-empty `homepage` field (i.e. they are in production), then updates
the README.md section delimited by:

    <!-- PROD-REPOS:START -->
    <!-- PROD-REPOS:END -->

Usage (local):
    GITHUB_TOKEN=<pat> python3 .github/scripts/update_prod_repos.py

Environment variables:
    GITHUB_TOKEN  – Optional but recommended to avoid rate-limiting.
    GITHUB_USER   – GitHub username/org to query (default: juancadev-io).
    README_PATH   – Path to the README file (default: README.md).
"""

import json
import os
import sys
import urllib.request
from urllib.error import HTTPError

START_MARKER = "<!-- PROD-REPOS:START -->"
END_MARKER = "<!-- PROD-REPOS:END -->"

GITHUB_USER = os.environ.get("GITHUB_USER", "juancadev-io")
README_PATH = os.environ.get("README_PATH", "README.md")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")


def fetch_repos(user: str) -> list[dict]:
    """Fetch all public repos for *user* with pagination."""
    repos: list[dict] = []
    page = 1
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"

    while True:
        url = (
            f"https://api.github.com/users/{user}/repos"
            f"?type=public&per_page=100&page={page}"
        )
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req) as resp:
                data = json.loads(resp.read().decode())
        except HTTPError as exc:
            print(f"GitHub API error {exc.code}: {exc.reason}", file=sys.stderr)
            sys.exit(1)

        if not data:
            break
        repos.extend(data)
        if len(data) < 100:
            break
        page += 1

    return repos


def filter_prod_repos(repos: list[dict]) -> list[dict]:
    """Keep only public repos with a non-empty homepage."""
    return [r for r in repos if r.get("homepage") and r["homepage"].strip()]


def build_section(repos: list[dict]) -> str:
    """Build the Markdown content that goes between the markers."""
    if not repos:
        return (
            f"{START_MARKER}\n"
            "<!-- This section is auto-generated. Do not edit manually. -->\n"
            "_No hay proyectos en producción todavía._\n"
            f"{END_MARKER}"
        )

    lines = [
        START_MARKER,
        "<!-- This section is auto-generated every Monday. Do not edit manually. -->",
        "",
        "## 🚀 Proyectos en producción",
        "",
        "| Repositorio | Producción | Descripción |",
        "| --- | --- | --- |",
    ]

    for repo in repos:
        name = repo["name"]
        repo_url = repo["html_url"]
        homepage = repo["homepage"].strip()
        description = (repo.get("description") or "").strip()
        description = description.replace("|", "\\|")
        lines.append(f"| [{name}]({repo_url}) | [🔗 {homepage}]({homepage}) | {description} |")

    lines += ["", END_MARKER]
    return "\n".join(lines)


def update_readme(path: str, new_section: str) -> bool:
    """Replace the section between markers in *path*. Returns True if changed."""
    with open(path, "r", encoding="utf-8") as fh:
        content = fh.read()

    if START_MARKER not in content or END_MARKER not in content:
        print(
            f"Markers not found in {path}. Add '{START_MARKER}' and '{END_MARKER}'.",
            file=sys.stderr,
        )
        sys.exit(1)

    start_idx = content.index(START_MARKER)
    end_idx = content.index(END_MARKER) + len(END_MARKER)
    current_section = content[start_idx:end_idx]

    if current_section == new_section:
        print("Section is already up-to-date. No changes made.")
        return False

    updated = content[:start_idx] + new_section + content[end_idx:]
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(updated)
    print(f"README updated: {path}")
    return True


def main() -> None:
    repos = fetch_repos(GITHUB_USER)
    prod_repos = filter_prod_repos(repos)
    # Sort deterministically: name ascending
    prod_repos.sort(key=lambda r: r["name"].lower())
    section = build_section(prod_repos)
    update_readme(README_PATH, section)
    sys.exit(0)


if __name__ == "__main__":
    main()
