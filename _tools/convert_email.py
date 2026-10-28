#!/usr/bin/env python3
"""
convert_email.py — Email / Calendar export converter to RAW/ markdown.

Converts:
  - Google Takeout MBOX files → raw/email/YYYYMMDD-subject-slug.md
  - ICS calendar files → raw/email/cal-YYYYMMDD-event-slug.md
  - EML files → raw/email/YYYYMMDD-subject-slug.md

Each output file has YAML frontmatter with metadata and body as plain text.

Usage:
    python _tools/convert_email.py path/to/export.mbox
    python _tools/convert_email.py path/to/calendar.ics
    python _tools/convert_email.py path/to/message.eml
    python _tools/convert_email.py path/to/folder/   (batch mode: scans for .mbox, .ics, .eml)

Standard library only.
"""

import email
import email.policy
import os
import re
import sys
from datetime import datetime
from email.utils import parsedate_to_datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
RAW_EMAIL_DIR = REPO_ROOT / "raw" / "email"


def slugify(text: str, max_len: int = 60) -> str:
    """Convert text to a clean kebab-case slug."""
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_]+', '-', text)
    text = re.sub(r'-+', '-', text).strip('-')
    return text[:max_len]


def extract_text_from_email(msg: email.message.Message) -> str:
    """Extract plain text body from an email message."""
    body_parts = []
    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            if ctype == "text/plain":
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or "utf-8"
                    body_parts.append(payload.decode(charset, errors="replace"))
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            charset = msg.get_content_charset() or "utf-8"
            body_parts.append(payload.decode(charset, errors="replace"))
    return "\n\n".join(body_parts).strip()


def convert_eml(filepath: Path) -> list:
    """Convert a single .eml file to markdown. Returns list of (filename, content)."""
    results = []
    raw = filepath.read_bytes()
    msg = email.message_from_bytes(raw, policy=email.policy.default)

    subject = str(msg.get("Subject", "no-subject"))
    sender = str(msg.get("From", "unknown"))
    to = str(msg.get("To", "unknown"))
    date_str = str(msg.get("Date", ""))

    try:
        dt = parsedate_to_datetime(date_str)
    except Exception:
        dt = datetime.now()

    date_prefix = dt.strftime("%Y%m%d")
    date_iso = dt.strftime("%Y-%m-%d")
    slug = slugify(subject)
    fname = f"{date_prefix}-{slug}.md"

    body = extract_text_from_email(msg)

    content = f"""---
title: "{subject}"
type: source
domain: work
source_type: email
source_from: "{sender}"
source_to: "{to}"
source_date: {date_iso}
ingest_date: {datetime.now().strftime("%Y-%m-%d")}
status: seed
tags:
  - email
  - raw-source
---

# {subject}

## Metadata
- **From**: {sender}
- **To**: {to}
- **Date**: {date_iso}
- **Original File**: `{filepath.name}`

---

## Body

{body}
"""
    results.append((fname, content))
    return results


def convert_mbox(filepath: Path) -> list:
    """Convert MBOX file to individual markdown files. Returns list of (filename, content)."""
    import mailbox
    results = []
    mbox = mailbox.mbox(str(filepath))
    count = 0
    for msg in mbox:
        subject = str(msg.get("Subject", "no-subject"))
        sender = str(msg.get("From", "unknown"))
        to = str(msg.get("To", "unknown"))
        date_str = str(msg.get("Date", ""))

        try:
            dt = parsedate_to_datetime(date_str)
        except Exception:
            dt = datetime.now()

        date_prefix = dt.strftime("%Y%m%d")
        date_iso = dt.strftime("%Y-%m-%d")
        slug = slugify(subject)
        # Add counter to avoid name collisions
        fname = f"{date_prefix}-{slug}-{count:04d}.md"

        body = extract_text_from_email(msg)

        content = f"""---
title: "{subject}"
type: source
domain: work
source_type: email-mbox
source_from: "{sender}"
source_to: "{to}"
source_date: {date_iso}
ingest_date: {datetime.now().strftime("%Y-%m-%d")}
status: seed
tags:
  - email
  - raw-source
---

# {subject}

## Metadata
- **From**: {sender}
- **To**: {to}
- **Date**: {date_iso}

---

## Body

{body}
"""
        results.append((fname, content))
        count += 1
    return results


def convert_ics(filepath: Path) -> list:
    """Convert ICS calendar file to markdown events. Returns list of (filename, content)."""
    results = []
    text = filepath.read_text(encoding="utf-8", errors="replace")

    # Simple ICS parser (stdlib-only, no icalendar lib)
    events = re.split(r'BEGIN:VEVENT', text)
    for i, block in enumerate(events[1:], 1):  # skip preamble
        # Extract fields
        def get_field(name: str, block: str) -> str:
            m = re.search(rf'^{name}[;:](.*)$', block, re.MULTILINE)
            return m.group(1).strip() if m else ""

        summary = get_field("SUMMARY", block)
        dtstart = get_field("DTSTART", block)
        dtend = get_field("DTEND", block)
        location = get_field("LOCATION", block)
        description = get_field("DESCRIPTION", block).replace("\\n", "\n").replace("\\,", ",")
        organizer = get_field("ORGANIZER", block)

        # Parse date
        date_clean = re.sub(r'[TZ]', ' ', dtstart).strip()[:8]
        try:
            dt = datetime.strptime(date_clean, "%Y%m%d")
        except Exception:
            dt = datetime.now()

        date_prefix = dt.strftime("%Y%m%d")
        date_iso = dt.strftime("%Y-%m-%d")
        slug = slugify(summary or f"event-{i}")
        fname = f"cal-{date_prefix}-{slug}.md"

        content = f"""---
title: "{summary}"
type: source
domain: work
source_type: calendar-event
source_date: {date_iso}
ingest_date: {datetime.now().strftime("%Y-%m-%d")}
status: seed
tags:
  - calendar
  - raw-source
---

# 📅 {summary}

## Event Details
- **Date**: {date_iso}
- **Start**: {dtstart}
- **End**: {dtend}
- **Location**: {location or "_N/A_"}
- **Organizer**: {organizer or "_N/A_"}

---

## Description

{description or "_No description._"}
"""
        results.append((fname, content))
    return results


def main():
    if len(sys.argv) < 2:
        print("Usage: python _tools/convert_email.py <file_or_folder>")
        print("  Supports: .eml, .mbox, .ics files or a folder containing them.")
        sys.exit(1)

    target = Path(sys.argv[1])
    RAW_EMAIL_DIR.mkdir(parents=True, exist_ok=True)

    files_to_process = []
    if target.is_dir():
        for ext in ("*.eml", "*.mbox", "*.ics"):
            files_to_process.extend(target.glob(ext))
            files_to_process.extend(target.rglob(ext))
    elif target.is_file():
        files_to_process = [target]
    else:
        print(f"❌ Path not found: {target}")
        sys.exit(1)

    if not files_to_process:
        print(f"⚠️ No .eml, .mbox, or .ics files found in {target}")
        sys.exit(0)

    total_created = 0
    for fpath in sorted(set(files_to_process)):
        ext = fpath.suffix.lower()
        print(f"[*] Processing {fpath.name} ({ext})...")

        if ext == ".eml":
            results = convert_eml(fpath)
        elif ext == ".mbox":
            results = convert_mbox(fpath)
        elif ext == ".ics":
            results = convert_ics(fpath)
        else:
            print(f"  [SKIP] Unsupported format: {ext}")
            continue

        for fname, content in results:
            out_path = RAW_EMAIL_DIR / fname
            if out_path.exists():
                print(f"  [SKIP] Already exists: {fname}")
                continue
            out_path.write_text(content, encoding="utf-8")
            print(f"  [+] Created: raw/email/{fname}")
            total_created += 1

    print(f"\n[SUCCESS] Converted {total_created} file(s) to raw/email/")


if __name__ == "__main__":
    main()
