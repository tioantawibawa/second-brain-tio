#!/usr/bin/env python3
"""
lint.py — Wiki Quality Assurance & Integrity Checker.

Reports:
  1. Broken [[wikilinks]] — target file does not exist
  2. Orphan pages — files with zero inbound links from any other page
  3. Missing required frontmatter fields (title, type, domain, status, updated)
  4. Source paths in frontmatter `sources:` that do not exist in raw/

Usage:
    python _tools/lint.py
    python _tools/lint.py --fix-fields    # Auto-add missing frontmatter fields (placeholder)
    python _tools/lint.py --verbose

Standard library only (no external dependencies).
"""

import os
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
WIKI_DIR = REPO_ROOT / "wiki"
RAW_DIR = REPO_ROOT / "raw"
CRM_DIR = REPO_ROOT / "crm"
JOURNAL_DIR = REPO_ROOT / "journal"
IN_MOTION_DIR = REPO_ROOT / "in_motion"
LATTICES_DIR = REPO_ROOT / "lattices"

# All directories that can contain linkable .md files
LINKABLE_DIRS = [WIKI_DIR, CRM_DIR, JOURNAL_DIR, IN_MOTION_DIR, LATTICES_DIR, RAW_DIR]

# Required frontmatter fields for wiki pages
REQUIRED_FIELDS = {"title", "type", "domain", "status", "updated"}

# Directories to skip
SKIP_DIRS = {".obsidian", "__pycache__", "node_modules", ".git", "_tools", "packages",
             "services", "scripts", "tools", "systemd", "system_triggers", "data"}


def parse_frontmatter(filepath: Path) -> dict:
    """Parse YAML frontmatter from a markdown file (stdlib-only)."""
    try:
        text = filepath.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return {}

    match = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
    if not match:
        return {}

    fm = {}
    raw_block = match.group(1)
    current_key = None
    list_buffer = []

    for line in raw_block.split("\n"):
        kv = re.match(r'^(\w[\w_-]*)\s*:\s*(.*)$', line)
        if kv and not line.startswith("  ") and not line.startswith("\t"):
            if current_key and list_buffer:
                fm[current_key] = list_buffer
                list_buffer = []
            current_key = kv.group(1)
            val = kv.group(2).strip().strip('"').strip("'")
            if val and not val.startswith("["):
                fm[current_key] = val
            elif val.startswith("[") and val.endswith("]"):
                items = [v.strip().strip('"').strip("'") for v in val[1:-1].split(",") if v.strip()]
                fm[current_key] = items
                current_key = None
        elif line.strip().startswith("- ") and current_key:
            item = line.strip()[2:].strip().strip('"').strip("'")
            list_buffer.append(item)

    if current_key and list_buffer:
        fm[current_key] = list_buffer

    return fm


def collect_all_md_files() -> dict:
    """Collect all .md files that can be targets of wikilinks.
    Returns dict mapping stem (basename without .md) -> list of absolute paths."""
    files_by_stem: dict = {}
    for search_dir in LINKABLE_DIRS:
        if not search_dir.exists():
            continue
        for root, dirs, files in os.walk(search_dir):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
            for fname in files:
                if fname.endswith(".md"):
                    stem = fname[:-3]  # remove .md
                    fpath = Path(root) / fname
                    files_by_stem.setdefault(stem, []).append(fpath)
    # Also check root-level .md files
    for f in REPO_ROOT.iterdir():
        if f.is_file() and f.suffix == ".md":
            stem = f.stem
            files_by_stem.setdefault(stem, []).append(f)
    return files_by_stem


def extract_wikilinks(filepath: Path) -> list:
    """Extract all [[wikilinks]] from a markdown file."""
    try:
        text = filepath.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return []
    # Match [[target]] or [[target|display]]
    return re.findall(r'\[\[([^\]|]+)(?:\|[^\]]+)?\]\]', text)


def lint_wiki(verbose: bool = False) -> dict:
    """Run all lint checks. Returns a report dict."""
    report = {
        "broken_links": [],      # (source_file, broken_target)
        "orphan_pages": [],      # files with zero inbound links
        "missing_fields": [],    # (file, missing_fields_list)
        "missing_sources": [],   # (file, source_path_that_doesnt_exist)
        "total_files": 0,
        "total_links": 0,
    }

    all_files = collect_all_md_files()
    all_stems = set(all_files.keys())

    # Track inbound links
    inbound_count: dict = {stem: 0 for stem in all_stems}

    # Scan wiki directory specifically for frontmatter checks
    wiki_files = []
    for root, dirs, files in os.walk(WIKI_DIR):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for fname in sorted(files):
            if fname.endswith(".md") and fname not in ("index.md", "log.md"):
                wiki_files.append(Path(root) / fname)

    report["total_files"] = len(wiki_files)

    # Check each wiki file
    for fpath in wiki_files:
        rel = fpath.relative_to(REPO_ROOT).as_posix()
        fm = parse_frontmatter(fpath)

        # 1. Check required frontmatter fields
        # Allow alternative field names
        present = set(fm.keys())
        alt_map = {"updated": {"updated", "updated_at", "ingest_date", "created_at", "date"}}
        missing = []
        for req in REQUIRED_FIELDS:
            alts = alt_map.get(req, {req})
            if not alts.intersection(present):
                missing.append(req)
        if missing:
            report["missing_fields"].append((rel, missing))
            if verbose:
                print(f"  [MISSING FIELDS] {rel}: {missing}")

        # 2. Check source paths in frontmatter
        sources = fm.get("sources", [])
        if isinstance(sources, str):
            sources = [sources]
        for src in sources:
            # Clean wikilink markers
            src_clean = src.strip("[]").replace("[[", "").replace("]]", "")
            src_path = REPO_ROOT / src_clean
            if not src_path.exists():
                # Also check with .md extension
                if not (REPO_ROOT / (src_clean + ".md")).exists():
                    report["missing_sources"].append((rel, src_clean))
                    if verbose:
                        print(f"  [MISSING SOURCE] {rel}: source '{src_clean}' not found")

        # 3. Check wikilinks
        links = extract_wikilinks(fpath)
        report["total_links"] += len(links)
        for target in links:
            # Normalize: remove path components, just check stem
            target_stem = target.split("/")[-1].replace(".md", "")
            if target_stem in all_stems:
                inbound_count[target_stem] = inbound_count.get(target_stem, 0) + 1
            else:
                report["broken_links"].append((rel, target))
                if verbose:
                    print(f"  [BROKEN LINK] {rel} -> [[{target}]]")

    # Also scan non-wiki dirs for outbound links (to track inbound)
    for search_dir in [CRM_DIR, JOURNAL_DIR, IN_MOTION_DIR, LATTICES_DIR]:
        if not search_dir.exists():
            continue
        for root, dirs, files in os.walk(search_dir):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
            for fname in files:
                if fname.endswith(".md"):
                    fpath = Path(root) / fname
                    links = extract_wikilinks(fpath)
                    for target in links:
                        target_stem = target.split("/")[-1].replace(".md", "")
                        if target_stem in inbound_count:
                            inbound_count[target_stem] = inbound_count.get(target_stem, 0) + 1

    # 4. Detect orphan pages (wiki files with zero inbound links)
    for fpath in wiki_files:
        stem = fpath.stem
        if inbound_count.get(stem, 0) == 0:
            rel = fpath.relative_to(REPO_ROOT).as_posix()
            report["orphan_pages"].append(rel)
            if verbose:
                print(f"  [ORPHAN] {rel}: no inbound links")

    return report


def print_report(report: dict):
    """Print a human-readable lint report."""
    print("\n" + "=" * 70)
    print("[LINT] SECOND BRAIN WIKI LINT REPORT")
    print("=" * 70)
    print(f"\n[SUMMARY] {report['total_files']} wiki files scanned, "
          f"{report['total_links']} wikilinks checked.\n")

    # Broken links
    broken = report["broken_links"]
    if broken:
        print(f"[FAIL] BROKEN WIKILINKS ({len(broken)}):")
        for src, target in broken:
            print(f"   {src} -> [[{target}]] (target not found)")
    else:
        print("[OK] No broken wikilinks.")

    # Orphan pages
    orphans = report["orphan_pages"]
    if orphans:
        print(f"\n[WARN] ORPHAN PAGES ({len(orphans)}) -- no inbound links:")
        for o in orphans:
            print(f"   {o}")
    else:
        print("\n[OK] No orphan pages.")

    # Missing fields
    missing = report["missing_fields"]
    if missing:
        print(f"\n[WARN] MISSING FRONTMATTER FIELDS ({len(missing)}):")
        for filepath, fields in missing:
            print(f"   {filepath}: missing {fields}")
    else:
        print("\n[OK] All wiki pages have required frontmatter fields.")

    # Missing sources
    msrc = report["missing_sources"]
    if msrc:
        print(f"\n[WARN] MISSING SOURCE PATHS ({len(msrc)}):")
        for filepath, src_path in msrc:
            print(f"   {filepath}: source '{src_path}' not found in raw/")
    else:
        print("\n[OK] All source paths are valid.")

    # Final verdict
    total_issues = len(broken) + len(orphans) + len(missing) + len(msrc)
    print(f"\n{'=' * 70}")
    if total_issues == 0:
        print("[PASS] VAULT CLEAN -- No issues detected.")
    else:
        print(f"[REPORT] {total_issues} total issue(s) found. Review and fix above.")
    print("=" * 70)


def main():
    verbose = "--verbose" in sys.argv or "-v" in sys.argv
    print(f"[*] Running wiki lint on {WIKI_DIR}...")
    report = lint_wiki(verbose=verbose)
    print_report(report)


if __name__ == "__main__":
    main()
