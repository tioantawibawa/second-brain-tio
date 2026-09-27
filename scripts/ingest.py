#!/usr/bin/env python3
"""
Ingest Pipeline: Second Brain (Momentum & Deliverable-Driven)
Tailored for: Deliverable-first, high-concurrency builder, executive-ready output.
Zero external pip dependencies (Pure Python 3 Standard Library).
Integrates with Google Gemini 3.8 Flash with graceful local heuristic fallback.
"""

import os
import sys
import json
import re
import argparse
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

def load_env():
    """Loads key-value pairs from .env into os.environ if not already set."""
    env_file = REPO_ROOT / ".env"
    if env_file.exists():
        with open(env_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                k = k.strip()
                v = v.strip().strip("\"'")
                if k and k not in os.environ:
                    os.environ[k] = v

def slugify(text: str) -> str:
    """Converts a title or string to clean kebab-case."""
    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    return text.strip("-")

def call_gemini_api(prompt: str, api_key: str, model: str = "gemini-3.8-flash") -> dict:
    """Calls Gemini REST API using urllib (standard library) with retry."""
    import time
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.2,
            "responseMimeType": "application/json"
        }
    }
    
    data = json.dumps(payload).encode("utf-8")
    
    max_retries = 2
    for attempt in range(max_retries + 1):
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                body = json.loads(resp.read().decode("utf-8"))
                raw_text = body["candidates"][0]["content"]["parts"][0]["text"]
                return json.loads(raw_text)
        except urllib.error.HTTPError as e:
            error_msg = e.read().decode("utf-8") if hasattr(e, "read") else str(e)
            if e.code in (429, 503) and attempt < max_retries:
                time.sleep(2 * (attempt + 1))
                continue
            raise RuntimeError(f"Gemini API HTTP Error {e.code}: {error_msg}")
        except Exception as e:
            if attempt < max_retries:
                time.sleep(2)
                continue
            raise RuntimeError(f"Gemini API request failed: {e}")

def local_heuristic_parse(raw_content: str, filename: str) -> dict:
    """Deterministic fallback parser if Gemini API is unavailable."""
    lines = [line.strip() for line in raw_content.splitlines() if line.strip()]
    
    # Extract title
    title = Path(filename).stem.replace("-", " ").replace("_", " ").title()
    for line in lines:
        if line.startswith("# "):
            title = line[2:].strip()
            break
            
    slug = slugify(title)
    
    # Extract action items
    action_items = []
    for line in lines:
        if re.search(r"^(- \[ \]|TODO|Action:|Perlu dikerjakan:)", line, re.IGNORECASE):
            clean_item = re.sub(r"^(- \[ \]|TODO:?|Action:?|Perlu dikerjakan:?)\s*", "", line, flags=re.IGNORECASE)
            action_items.append(f"- [ ] {clean_item}")
            
    if not action_items:
        action_items = [
            "- [ ] Review rancangan arsitektur dan spesifikasi teknis",
            "- [ ] Implementasikan prototipe dasar dan verifikasi lokal",
            "- [ ] Evaluasi kesiapan deployment atau integrasi production"
        ]
        
    # Classify stream & folder
    lower_content = raw_content.lower()
    if any(k in lower_content for k in ["klien", "enterprise", "client", "roadmap perusahaan", "deliverable kerja"]):
        stream = "core_work"
        target_folder = "in_motion/core_work"
        note_type = "in_motion"
        status = "active"
    elif any(k in lower_content for k in ["agent", "rag", "bot", "saas", "side project", "eksperimen", "builder"]):
        stream = "side_builder"
        target_folder = "in_motion/side_builder"
        note_type = "in_motion"
        status = "active"
    elif any(k in lower_content for k in ["mental model", "framework", "hukum", "prinsip"]):
        stream = "meta_system"
        target_folder = "lattices/mental_models"
        note_type = "lattice"
        status = "evergreen"
    else:
        stream = "meta_system"
        target_folder = "lattices/playbooks"
        note_type = "lattice"
        status = "evergreen"

    # Entities extraction (simple capitalized / tech terms + existing wikilinks)
    found_entities = set()
    raw_wikilinks = re.findall(r"\[\[(.*?)\]\]", raw_content)
    for rw in raw_wikilinks:
        target = rw.split("|")[0].strip()
        found_entities.add(f"[[{target}]]")

    tech_keywords = [
        "python", "fastapi", "docker", "postgres", "redis", "gemini", 
        "obsidian", "neovim", "rag", "langchain", "agent", "vps", "git"
    ]
    for kw in tech_keywords:
        if kw in lower_content:
            found_entities.add(f"[[{kw}-playbook]]")
            
    key_entities = sorted(list(found_entities))
    if not key_entities:
        key_entities = [f"[[{slug}-architecture]]"]

    # Core insights
    core_insights = [
        f"Inisiatif {title} berorientasi langsung pada implementasi teknis dan output terukur.",
        "Komponen modular siap diintegrasikan dengan arsitektur sistem yang ada."
    ]
    for line in lines[:5]:
        if not line.startswith("#") and len(line) > 30:
            core_insights.append(line)
            break

    today = datetime.now().strftime("%Y-%m-%d")
    
    # Generate structured markdown
    formatted_md = f"""---
title: "{title}"
id: "{today.replace('-', '')}-{slug}"
type: {note_type}
stream: {stream}
status: {status}
created_at: {today}
updated_at: {today}
tags:
  - {stream.replace('_', '-')}
  - second-brain-ingest
links:
{chr(10).join(f'  - "{e}"' for e in key_entities)}
---

# {title}

## 1. Executive Summary & Core Insights
{chr(10).join(f"- {ci}" for ci in core_insights)}

---

## 2. Key Entities & Knowledge Connections
| Entitas / Modul | Kategori | Relasi Sistem |
| :--- | :--- | :--- |
"""
    for entity in key_entities:
        formatted_md += f"| {entity} | Knowledge Lattice | Fondasi arsitektur pendukung |\n"

    formatted_md += f"""
---

## 3. Action Items & Execution Triggers
{chr(10).join(action_items)}

---

## 4. Raw Dump Context & Original Notes
```text
{raw_content.strip()}
```
"""
    return {
        "title": title,
        "slug": slug,
        "stream": stream,
        "target_folder": target_folder,
        "status": status,
        "type": note_type,
        "key_entities": key_entities,
        "action_items": action_items,
        "formatted_markdown": formatted_md
    }

def ai_parse_note(raw_content: str, filename: str, api_key: str, model: str) -> dict:
    """Uses Gemini API to synthesize executive-ready Second Brain note."""
    prompt = f"""
You are the AI Cognitive Ingestion Engine for an AI Systems Engineer & Knowledge Architecture Specialist.
The user has the following cognitive profile:
- deliverable-first ("buatkan X", clear concrete output, rarely open-ended)
- high concurrency (multi-lane parallel: core professional work vs side-project builder running at the same time)
- output standard: statistically grounded, executive-ready, visually clean, structured tables/checklists
- language: Indonesian default, English for technical/professional terms
- follow-through: ideas pushed to execution/deployment, not stuck in theoretical discourse.

Analyze the following raw dump / note from `{filename}`.

Produce a JSON response with the following exact keys:
1. "title": Crisp title (Executive and deliverable-focused).
2. "slug": kebab-case identifier (e.g., "autonomous-eval-harness").
3. "stream": One of ["core_work", "side_builder", "meta_system"].
4. "target_folder": One of ["in_motion/core_work", "in_motion/side_builder", "lattices/mental_models", "lattices/playbooks"].
5. "type": One of ["in_motion", "lattice"].
6. "status": One of ["active", "incubating", "evergreen"].
7. "tags": Array of strings (e.g. ["ai-agents", "evaluation", "fastapi"]).
8. "core_insights": Array of 2-4 grounded, executive-ready insight bullet points.
9. "key_entities": Array of 2-5 wikilinks strings with double brackets (e.g. ["[[latency-optimization-playbook]]", "[[agent-orchestration]]"]).
10. "action_items": Array of concrete checklist items starting with "- [ ]".
11. "formatted_markdown": Complete GitHub Flavored Markdown note string including YAML frontmatter at the top, executive summary, tables for metrics/entities, Mermaid diagram if helpful, and action triggers checklist.

Raw Dump Content:
\"\"\"
{raw_content}
\"\"\"
"""
    try:
        parsed = call_gemini_api(prompt, api_key, model)
        if "slug" not in parsed or not parsed.get("slug"):
            parsed["slug"] = slugify(parsed.get("title", Path(filename).stem))
        return parsed
    except Exception as e:
        print(f"[!] Warning: Gemini API parsing failed ({e}). Falling back to local heuristic parser.")
        return local_heuristic_parse(raw_content, filename)

def process_file(file_path: Path, dry_run: bool = False, keep_raw: bool = False, forced_target: str = None) -> bool:
    """Processes a single raw note file."""
    if not file_path.exists():
        print(f"[-] File not found: {file_path}")
        return False
        
    print(f"\n[*] Processing: {file_path.name} ...")
    raw_content = file_path.read_text(encoding="utf-8")
    if not raw_content.strip():
        print(f"[-] Skipping empty file: {file_path.name}")
        return False

    try:
        import ai_engine
        data, used_model = ai_engine.parse_text_with_ai(raw_content, file_path.name)
        print(f"[*] Processed using AI model: {used_model}")
    except Exception as e:
        print(f"[!] AI Engine failed ({e}). Using local heuristic extraction engine...")
        data = local_heuristic_parse(raw_content, file_path.name)

    slug = data.get("slug", slugify(data.get("title", file_path.stem)))
    target_rel_folder = forced_target if forced_target else data.get("target_folder", "in_motion/side_builder")
    target_dir = REPO_ROOT / target_rel_folder
    target_dir.mkdir(parents=True, exist_ok=True)
    
    target_file = target_dir / f"{slug}.md"
    content = data.get("formatted_markdown", "")
    
    if dry_run:
        print("\n" + "="*50 + " DRY RUN OUTPUT " + "="*50)
        print(f"Target Path: {target_file.relative_to(REPO_ROOT)}")
        print(content)
        print("="*116 + "\n")
        return True

    target_file.write_text(content, encoding="utf-8")
    print(f"[+] Successfully generated: {target_file.relative_to(REPO_ROOT)}")

    # Move raw file to archive inside inbox_raw/.archive
    if not keep_raw and file_path.parent == REPO_ROOT / "inbox_raw":
        archive_dir = REPO_ROOT / "inbox_raw" / ".archive"
        archive_dir.mkdir(parents=True, exist_ok=True)
        dest_archive = archive_dir / f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{file_path.name}"
        file_path.rename(dest_archive)
        print(f"[+] Archived raw file to: {dest_archive.relative_to(REPO_ROOT)}")

    return True

def main():
    load_env()
    parser = argparse.ArgumentParser(description="Second Brain Ingest Engine (Deliverable-First & Gemini AI-powered)")
    parser.add_argument("--file", "-f", help="Path to single markdown or text file in inbox_raw/")
    parser.add_argument("--all", "-a", action="store_true", help="Process all files currently in inbox_raw/")
    parser.add_argument("--dry-run", "-d", action="store_true", help="Print result to terminal without writing or moving files")
    parser.add_argument("--keep-raw", action="store_true", help="Do not move raw files to .archive after ingest")
    parser.add_argument("--target", "-t", help="Force target subfolder (e.g. in_motion/core_work, in_motion/side_builder, lattices/mental_models)")

    args = parser.parse_args()

    if args.file:
        file_path = Path(args.file)
        if not file_path.is_absolute():
            file_path = (REPO_ROOT / file_path).resolve()
        process_file(file_path, dry_run=args.dry_run, keep_raw=args.keep_raw, forced_target=args.target)
    elif args.all:
        inbox_dir = REPO_ROOT / "inbox_raw"
        raw_files = [f for f in inbox_dir.iterdir() if f.is_file() and not f.name.startswith(".")]
        if not raw_files:
            print("[*] inbox_raw/ is completely clear. No files to ingest.")
            return
        print(f"[*] Found {len(raw_files)} item(s) in inbox_raw/...")
        for rf in raw_files:
            process_file(rf, dry_run=args.dry_run, keep_raw=args.keep_raw, forced_target=args.target)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
