#!/usr/bin/env python3
"""
convert_telegram.py — Telegram bot capture converter to RAW/ markdown.

Converts existing Telegram bot captures from inbox_raw/ and journal/quick_captures.md
into structured markdown files in raw/telegram/.

Also supports re-parsing raw Telegram bot dump files directly.

Usage:
    python _tools/convert_telegram.py                    # Auto-scan inbox_raw/ and journal/
    python _tools/convert_telegram.py path/to/file.md    # Convert specific file
    python _tools/convert_telegram.py --scan-inbox       # Scan inbox_raw/ for unprocessed captures

Standard library only.
"""

import os
import re
import sys
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
RAW_TELEGRAM_DIR = REPO_ROOT / "raw" / "telegram"
INBOX_RAW_DIR = REPO_ROOT / "inbox_raw"
INBOX_ARCHIVE_DIR = INBOX_RAW_DIR / ".archive"
JOURNAL_DIR = REPO_ROOT / "journal"
QUICK_CAPTURES = JOURNAL_DIR / "quick_captures.md"


def slugify(text: str, max_len: int = 60) -> str:
    """Convert text to a clean kebab-case slug."""
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_]+', '-', text)
    text = re.sub(r'-+', '-', text).strip('-')
    return text[:max_len] if text else "capture"


def parse_quick_captures(filepath: Path) -> list:
    """Parse journal/quick_captures.md into individual capture entries.
    Format expected:
      ### YYYY-MM-DD HH:MM:SS
      content text
      ---
    """
    if not filepath.exists():
        return []

    text = filepath.read_text(encoding="utf-8", errors="replace")
    # Split by the separator pattern
    entries = []
    blocks = re.split(r'\n---\n', text)

    for block in blocks:
        block = block.strip()
        if not block:
            continue

        # Try to extract timestamp header
        header_match = re.match(r'###?\s*(\d{4}-\d{2}-\d{2}[\sT_]\d{2}:\d{2}(?::\d{2})?)', block)
        if header_match:
            ts_str = header_match.group(1).replace("_", " ").replace("T", " ")
            try:
                dt = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                try:
                    dt = datetime.strptime(ts_str, "%Y-%m-%d %H:%M")
                except ValueError:
                    dt = datetime.now()

            content = block[header_match.end():].strip()
        else:
            dt = datetime.now()
            content = block

        if content and len(content) > 3:
            entries.append({"timestamp": dt, "content": content})

    return entries


def parse_inbox_file(filepath: Path) -> list:
    """Parse a single inbox_raw file into a structured capture."""
    if not filepath.exists() or not filepath.suffix == ".md":
        return []

    text = filepath.read_text(encoding="utf-8", errors="replace")
    fname = filepath.stem

    # Try to extract timestamp from filename (format: YYYYMMDDHHMMSS_...)
    ts_match = re.match(r'(\d{4})(\d{2})(\d{2})_?(\d{2})?(\d{2})?(\d{2})?', fname)
    if ts_match:
        groups = ts_match.groups()
        y, m, d = groups[0], groups[1], groups[2]
        h = groups[3] or "00"
        mi = groups[4] or "00"
        s = groups[5] or "00"
        try:
            dt = datetime(int(y), int(m), int(d), int(h), int(mi), int(s))
        except ValueError:
            dt = datetime.now()
    else:
        dt = datetime.now()

    # Extract frontmatter if exists
    fm = {}
    body = text
    fm_match = re.match(r'^---\s*\n(.*?)\n---\s*\n(.*)', text, re.DOTALL)
    if fm_match:
        fm_block = fm_match.group(1)
        body = fm_match.group(2).strip()
        for line in fm_block.split("\n"):
            kv = re.match(r'^(\w[\w_-]*)\s*:\s*(.+)$', line)
            if kv:
                fm[kv.group(1)] = kv.group(2).strip().strip('"')

    title = fm.get("title", body[:60].replace("\n", " ").strip())

    return [{"timestamp": dt, "content": body, "title": title, "source_file": filepath.name, "frontmatter": fm}]


def convert_to_raw_md(entry: dict) -> tuple:
    """Convert a single capture entry to (filename, markdown_content)."""
    dt = entry["timestamp"]
    content = entry["content"]
    title = entry.get("title", content[:60].replace("\n", " ").strip())
    source_file = entry.get("source_file", "quick_captures.md")

    date_prefix = dt.strftime("%Y%m%d-%H%M")
    date_iso = dt.strftime("%Y-%m-%d")
    slug = slugify(title[:50])
    fname = f"tg-{date_prefix}-{slug}.md"

    # Detect content type
    has_url = bool(re.search(r'https?://', content))
    has_code = bool(re.search(r'```', content))
    content_type = "web-clip" if has_url else ("code-snippet" if has_code else "quick-thought")

    md = f"""---
title: "{title[:80]}"
type: source
domain: work
source_type: telegram-capture
source_channel: telegram-bot
source_date: {date_iso}
source_file: "{source_file}"
ingest_date: {datetime.now().strftime("%Y-%m-%d")}
status: seed
tags:
  - telegram
  - {content_type}
  - raw-source
---

# {title[:80]}

**Captured**: {dt.strftime("%Y-%m-%d %H:%M:%S")} via Telegram Bot
**Source**: `{source_file}`
**Type**: {content_type}

---

{content}
"""
    return (fname, md)


def main():
    RAW_TELEGRAM_DIR.mkdir(parents=True, exist_ok=True)

    all_entries = []

    if len(sys.argv) > 1 and sys.argv[1] != "--scan-inbox":
        # Convert specific file
        target = Path(sys.argv[1])
        if target.is_file():
            all_entries.extend(parse_inbox_file(target))
        else:
            print(f"❌ File not found: {target}")
            sys.exit(1)
    else:
        # Auto-scan mode
        print("[*] Scanning journal/quick_captures.md...")
        if QUICK_CAPTURES.exists():
            captures = parse_quick_captures(QUICK_CAPTURES)
            all_entries.extend(captures)
            print(f"  Found {len(captures)} quick captures.")

        print("[*] Scanning inbox_raw/ for telegram captures...")
        scan_dirs = [INBOX_RAW_DIR]
        if INBOX_ARCHIVE_DIR.exists():
            scan_dirs.append(INBOX_ARCHIVE_DIR)

        for scan_dir in scan_dirs:
            if not scan_dir.exists():
                continue
            for fpath in sorted(scan_dir.iterdir()):
                if fpath.suffix == ".md" and "telegram" in fpath.stem.lower():
                    entries = parse_inbox_file(fpath)
                    all_entries.extend(entries)
            count = sum(1 for f in scan_dir.iterdir() if f.suffix == ".md" and "telegram" in f.stem.lower())
            print(f"  Found {count} telegram dump files in {scan_dir.relative_to(REPO_ROOT)}")

    if not all_entries:
        print("⚠️ No Telegram captures found to convert.")
        sys.exit(0)

    total_created = 0
    total_skipped = 0
    for entry in all_entries:
        fname, content = convert_to_raw_md(entry)
        out_path = RAW_TELEGRAM_DIR / fname
        if out_path.exists():
            total_skipped += 1
            continue
        out_path.write_text(content, encoding="utf-8")
        print(f"  [+] Created: raw/telegram/{fname}")
        total_created += 1

    print(f"\n[SUCCESS] Created {total_created} file(s) in raw/telegram/ "
          f"({total_skipped} skipped as duplicates)")


if __name__ == "__main__":
    main()
