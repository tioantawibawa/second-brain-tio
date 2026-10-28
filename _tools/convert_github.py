#!/usr/bin/env python3
"""
convert_github.py — GitHub export converter to RAW/ markdown.

Converts GitHub data to structured markdown files in raw/github/.

Modes:
  1. JSON export (from GitHub API or gh CLI):
     python _tools/convert_github.py issues path/to/issues.json
     python _tools/convert_github.py prs path/to/pulls.json
     python _tools/convert_github.py repos path/to/repos.json

  2. Live fetch via `gh` CLI (if installed):
     python _tools/convert_github.py fetch-issues owner/repo
     python _tools/convert_github.py fetch-prs owner/repo
     python _tools/convert_github.py fetch-repos

Standard library only (uses subprocess for `gh` CLI calls).
"""

import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
RAW_GITHUB_DIR = REPO_ROOT / "raw" / "github"


def slugify(text: str, max_len: int = 60) -> str:
    """Convert text to a clean kebab-case slug."""
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_]+', '-', text)
    text = re.sub(r'-+', '-', text).strip('-')
    return text[:max_len]


def convert_issues_json(filepath: Path) -> list:
    """Convert GitHub issues JSON to markdown files."""
    data = json.loads(filepath.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        data = [data]

    results = []
    for issue in data:
        number = issue.get("number", 0)
        title = issue.get("title", "untitled")
        state = issue.get("state", "unknown")
        body = issue.get("body", "") or ""
        user = issue.get("user", {}).get("login", "unknown")
        created = issue.get("created_at", "")[:10]
        updated = issue.get("updated_at", "")[:10]
        labels = [l.get("name", "") for l in issue.get("labels", [])]
        repo_url = issue.get("repository_url", issue.get("html_url", ""))
        html_url = issue.get("html_url", "")
        comments_list = issue.get("comments_data", [])

        slug = slugify(title)
        fname = f"issue-{number:04d}-{slug}.md"

        labels_yaml = "\n".join(f"  - {l}" for l in labels) if labels else "  - none"
        comments_section = ""
        if comments_list:
            comments_section = "\n## Comments\n\n"
            for c in comments_list:
                c_user = c.get("user", {}).get("login", "unknown")
                c_date = c.get("created_at", "")[:10]
                c_body = c.get("body", "")
                comments_section += f"### {c_user} ({c_date})\n\n{c_body}\n\n---\n\n"

        content = f"""---
title: "#{number} {title}"
type: source
domain: engineering
source_type: github-issue
source_url: "{html_url}"
source_repo: "{repo_url}"
source_author: "{user}"
source_date: {created}
source_state: {state}
ingest_date: {datetime.now().strftime("%Y-%m-%d")}
status: seed
tags:
  - github
  - issue
{labels_yaml}
---

# #{number} {title}

## Metadata
- **State**: `{state}`
- **Author**: @{user}
- **Created**: {created}
- **Updated**: {updated}
- **Labels**: {', '.join(labels) if labels else '_none_'}
- **URL**: [{html_url}]({html_url})

---

## Body

{body}
{comments_section}"""
        results.append((fname, content))
    return results


def convert_prs_json(filepath: Path) -> list:
    """Convert GitHub pull requests JSON to markdown files."""
    data = json.loads(filepath.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        data = [data]

    results = []
    for pr in data:
        number = pr.get("number", 0)
        title = pr.get("title", "untitled")
        state = pr.get("state", "unknown")
        merged = pr.get("merged", False)
        body = pr.get("body", "") or ""
        user = pr.get("user", {}).get("login", "unknown")
        created = pr.get("created_at", "")[:10]
        html_url = pr.get("html_url", "")
        base_branch = pr.get("base", {}).get("ref", "main")
        head_branch = pr.get("head", {}).get("ref", "unknown")

        slug = slugify(title)
        fname = f"pr-{number:04d}-{slug}.md"

        status_label = "merged" if merged else state
        content = f"""---
title: "PR #{number} {title}"
type: source
domain: engineering
source_type: github-pr
source_url: "{html_url}"
source_author: "{user}"
source_date: {created}
source_state: {status_label}
ingest_date: {datetime.now().strftime("%Y-%m-%d")}
status: seed
tags:
  - github
  - pull-request
---

# PR #{number} {title}

## Metadata
- **State**: `{status_label}`
- **Author**: @{user}
- **Created**: {created}
- **Branch**: `{head_branch}` → `{base_branch}`
- **URL**: [{html_url}]({html_url})

---

## Description

{body}
"""
        results.append((fname, content))
    return results


def convert_repos_json(filepath: Path) -> list:
    """Convert GitHub repos JSON to markdown files."""
    data = json.loads(filepath.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        data = [data]

    results = []
    for repo in data:
        name = repo.get("name", "unknown")
        full_name = repo.get("full_name", name)
        description = repo.get("description", "") or ""
        language = repo.get("language", "unknown")
        private = repo.get("private", False)
        html_url = repo.get("html_url", "")
        created = repo.get("created_at", "")[:10]
        updated = repo.get("pushed_at", repo.get("updated_at", ""))[:10]
        stars = repo.get("stargazers_count", 0)
        topics = repo.get("topics", [])

        slug = slugify(name)
        fname = f"repo-{slug}.md"

        topics_yaml = "\n".join(f"  - {t}" for t in topics) if topics else ""
        content = f"""---
title: "Repo: {full_name}"
type: source
domain: engineering
source_type: github-repo
source_url: "{html_url}"
source_date: {created}
ingest_date: {datetime.now().strftime("%Y-%m-%d")}
status: seed
tags:
  - github
  - repository
  - {language.lower() if language else 'unknown'}
{topics_yaml}
---

# {full_name}

## Metadata
- **Language**: {language}
- **Visibility**: {'Private' if private else 'Public'}
- **Created**: {created}
- **Last Push**: {updated}
- **Stars**: {stars}
- **URL**: [{html_url}]({html_url})

---

## Description

{description or "_No description._"}
"""
        results.append((fname, content))
    return results


def fetch_and_convert(mode: str, repo: str = "") -> list:
    """Fetch data using gh CLI and convert."""
    try:
        subprocess.run(["gh", "--version"], capture_output=True, check=True)
    except (FileNotFoundError, subprocess.CalledProcessError):
        print("❌ `gh` CLI not found or not authenticated. Install: https://cli.github.com/")
        print("   Alternative: export JSON manually and use the file-based converter.")
        sys.exit(1)

    if mode == "fetch-issues" and repo:
        print(f"[*] Fetching issues from {repo}...")
        result = subprocess.run(
            ["gh", "api", f"repos/{repo}/issues", "--paginate", "-q", ".[]"],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            print(f"❌ Failed: {result.stderr}")
            return []
        data = json.loads(f"[{','.join(result.stdout.strip().split(chr(10)))}]")
        # Write temp JSON and convert
        tmp = RAW_GITHUB_DIR / "_tmp_issues.json"
        tmp.write_text(json.dumps(data), encoding="utf-8")
        results = convert_issues_json(tmp)
        tmp.unlink()
        return results

    elif mode == "fetch-prs" and repo:
        print(f"[*] Fetching PRs from {repo}...")
        result = subprocess.run(
            ["gh", "api", f"repos/{repo}/pulls?state=all", "--paginate"],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            print(f"❌ Failed: {result.stderr}")
            return []
        data = json.loads(result.stdout)
        tmp = RAW_GITHUB_DIR / "_tmp_prs.json"
        tmp.write_text(json.dumps(data), encoding="utf-8")
        results = convert_prs_json(tmp)
        tmp.unlink()
        return results

    elif mode == "fetch-repos":
        print("[*] Fetching your repos...")
        result = subprocess.run(
            ["gh", "repo", "list", "--json", "name,fullName,description,language,isPrivate,url,createdAt,pushedAt,stargazerCount"],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            print(f"❌ Failed: {result.stderr}")
            return []
        data = json.loads(result.stdout)
        # Map gh CLI fields to GitHub API fields
        for r in data:
            r["full_name"] = r.pop("fullName", r.get("name", ""))
            r["private"] = r.pop("isPrivate", False)
            r["html_url"] = r.pop("url", "")
            r["created_at"] = r.pop("createdAt", "")
            r["pushed_at"] = r.pop("pushedAt", "")
            r["stargazers_count"] = r.pop("stargazerCount", 0)
        tmp = RAW_GITHUB_DIR / "_tmp_repos.json"
        tmp.write_text(json.dumps(data), encoding="utf-8")
        results = convert_repos_json(tmp)
        tmp.unlink()
        return results

    return []


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python _tools/convert_github.py issues <issues.json>")
        print("  python _tools/convert_github.py prs <pulls.json>")
        print("  python _tools/convert_github.py repos <repos.json>")
        print("  python _tools/convert_github.py fetch-issues owner/repo")
        print("  python _tools/convert_github.py fetch-prs owner/repo")
        print("  python _tools/convert_github.py fetch-repos")
        sys.exit(1)

    RAW_GITHUB_DIR.mkdir(parents=True, exist_ok=True)
    mode = sys.argv[1]

    if mode in ("fetch-issues", "fetch-prs", "fetch-repos"):
        repo = sys.argv[2] if len(sys.argv) > 2 else ""
        results = fetch_and_convert(mode, repo)
    elif mode == "issues":
        results = convert_issues_json(Path(sys.argv[2]))
    elif mode == "prs":
        results = convert_prs_json(Path(sys.argv[2]))
    elif mode == "repos":
        results = convert_repos_json(Path(sys.argv[2]))
    else:
        print(f"❌ Unknown mode: {mode}")
        sys.exit(1)

    total = 0
    for fname, content in results:
        out_path = RAW_GITHUB_DIR / fname
        if out_path.exists():
            print(f"  [SKIP] {fname}")
            continue
        out_path.write_text(content, encoding="utf-8")
        print(f"  [+] Created: raw/github/{fname}")
        total += 1

    print(f"\n[SUCCESS] Converted {total} file(s) to raw/github/")


if __name__ == "__main__":
    main()
