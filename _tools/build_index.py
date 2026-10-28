#!/usr/bin/env python3
"""
build_index.py — Builds wiki/index.md from YAML frontmatter.

Scans all .md files in wiki/ (recursively), parses frontmatter,
and generates a structured catalogue grouped by domain and type.

Usage:
    python _tools/build_index.py
    python _tools/build_index.py --verbose

Standard library only (no external dependencies).
"""

import os
import re
import sys
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
WIKI_DIR = REPO_ROOT / "wiki"
INDEX_PATH = WIKI_DIR / "index.md"

# Directories to skip during scanning
SKIP_DIRS = {".obsidian", "__pycache__", "node_modules", ".git"}

# Domain display order
DOMAIN_ORDER = ["work", "engineering", "private", "_unclassified"]
# Type display order within each domain
TYPE_ORDER = ["source", "project", "topic", "person", "synthesis", "journal", "war-room", "_other"]
TYPE_LABELS = {
    "source": "📄 Sources",
    "project": "🚀 Projects",
    "topic": "💡 Topics",
    "person": "👤 People",
    "synthesis": "🔗 Syntheses",
    "journal": "📓 Journal",
    "war-room": "💀 War Room",
    "_other": "📦 Other",
}
DOMAIN_LABELS = {
    "work": "💼 Work — Bisnis, Kontrak & Konsultasi",
    "engineering": "⚙️ Engineering — Arsitektur, AI/ML & Infrastruktur",
    "private": "🔒 Private",
    "_unclassified": "📂 Unclassified (Legacy / No Domain)",
}


def parse_frontmatter(filepath: Path) -> dict:
    """Parse YAML frontmatter from a markdown file (stdlib-only, no yaml lib)."""
    try:
        text = filepath.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return {}

    # Match --- ... --- block at the start
    match = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
    if not match:
        return {}

    fm = {}
    raw_block = match.group(1)
    current_key = None
    list_buffer = []

    for line in raw_block.split("\n"):
        stripped = line.strip()
        # Key: value
        kv = re.match(r'^(\w[\w_-]*)\s*:\s*(.*)$', line)
        if kv and not line.startswith("  ") and not line.startswith("\t"):
            # Save previous list
            if current_key and list_buffer:
                fm[current_key] = list_buffer
                list_buffer = []
            current_key = kv.group(1)
            val = kv.group(2).strip().strip('"').strip("'")
            if val and not val.startswith("["):
                fm[current_key] = val
            elif val.startswith("[") and val.endswith("]"):
                # Inline list: [a, b, c]
                items = [v.strip().strip('"').strip("'") for v in val[1:-1].split(",") if v.strip()]
                fm[current_key] = items
                current_key = None
            # else: multi-line list follows
        elif stripped.startswith("- ") and current_key:
            item = stripped[2:].strip().strip('"').strip("'")
            list_buffer.append(item)

    if current_key and list_buffer:
        fm[current_key] = list_buffer

    return fm


def scan_wiki(verbose: bool = False) -> list:
    """Scan all .md files in wiki/ and extract frontmatter metadata."""
    entries = []
    for root, dirs, files in os.walk(WIKI_DIR):
        # Prune skip dirs
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for fname in sorted(files):
            if not fname.endswith(".md"):
                continue
            if fname in ("index.md", "log.md"):
                continue

            fpath = Path(root) / fname
            rel = fpath.relative_to(WIKI_DIR).as_posix()
            fm = parse_frontmatter(fpath)

            title = fm.get("title", fname.replace(".md", "").replace("-", " ").title())
            domain = fm.get("domain", "_unclassified")
            ftype = fm.get("type", "_other")
            status = fm.get("status", "—")
            updated = fm.get("updated", fm.get("updated_at", fm.get("ingest_date", "—")))
            summary = fm.get("summary", "")
            tags = fm.get("tags", [])
            if isinstance(tags, str):
                tags = [tags]

            # Infer domain from path if not in frontmatter
            if domain == "_unclassified":
                parts = rel.split("/")
                if len(parts) >= 2 and parts[0] in ("work", "engineering", "private"):
                    domain = parts[0]

            # Infer type from path if not in frontmatter
            if ftype == "_other":
                parts = rel.split("/")
                if len(parts) >= 2:
                    type_map = {"sources": "source", "projects": "project", "topics": "topic",
                                "people": "person", "syntheses": "synthesis"}
                    for p in parts:
                        if p in type_map:
                            ftype = type_map[p]
                            break

            wikilink = fname.replace(".md", "")
            entry = {
                "title": title,
                "domain": domain if domain in DOMAIN_ORDER else "_unclassified",
                "type": ftype if ftype in TYPE_ORDER else "_other",
                "status": status,
                "updated": str(updated),
                "summary": summary,
                "tags": tags,
                "wikilink": wikilink,
                "relpath": rel,
            }
            entries.append(entry)
            if verbose:
                print(f"  [SCAN] {rel} -> domain={domain} type={ftype} status={status}")

    return entries


def build_index_md(entries: list) -> str:
    """Generate the index.md content grouped by domain and type."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [
        "---",
        'title: "Second Brain Wiki Index"',
        "type: meta",
        "status: evergreen",
        f"updated: {datetime.now().strftime('%Y-%m-%d')}",
        "tags:",
        "  - meta",
        "  - index",
        "---",
        "",
        "# 🧠 Second Brain Wiki Index",
        "",
        f"> Auto-generated by `_tools/build_index.py` pada `{now}`.",
        f"> Total halaman: **{len(entries)}**",
        "",
    ]

    # Group by domain, then by type
    grouped: dict = {}
    for e in entries:
        d = e["domain"]
        t = e["type"]
        grouped.setdefault(d, {}).setdefault(t, []).append(e)

    for domain in DOMAIN_ORDER:
        if domain not in grouped:
            continue
        domain_entries = grouped[domain]
        domain_label = DOMAIN_LABELS.get(domain, domain)
        total_in_domain = sum(len(v) for v in domain_entries.values())
        lines.append(f"## {domain_label} ({total_in_domain})")
        lines.append("")

        for ttype in TYPE_ORDER:
            if ttype not in domain_entries:
                continue
            type_label = TYPE_LABELS.get(ttype, ttype)
            items = sorted(domain_entries[ttype], key=lambda x: x["title"].lower())
            lines.append(f"### {type_label}")
            lines.append("")
            lines.append("| Halaman | Status | Updated | Summary |")
            lines.append("| ------- | ------ | ------- | ------- |")
            for item in items:
                link = f"[[{item['wikilink']}|{item['title']}]]"
                summary = item["summary"][:80] + "…" if len(item["summary"]) > 80 else item["summary"]
                lines.append(f"| {link} | `{item['status']}` | {item['updated']} | {summary} |")
            lines.append("")

    # Legacy / root-level files without domain
    lines.append("---")
    lines.append("")
    lines.append("*Index ini di-rebuild otomatis. Jalankan: `python _tools/build_index.py`*")
    lines.append("")

    return "\n".join(lines)


def main():
    verbose = "--verbose" in sys.argv or "-v" in sys.argv
    print(f"[*] Scanning wiki/ at {WIKI_DIR}...")
    entries = scan_wiki(verbose=verbose)
    print(f"[+] Found {len(entries)} wiki pages.")

    content = build_index_md(entries)
    INDEX_PATH.write_text(content, encoding="utf-8")
    print(f"[+] Built wiki/index.md ({len(content)} bytes)")
    print(f"[SUCCESS] Index rebuilt: {INDEX_PATH}")


if __name__ == "__main__":
    main()
