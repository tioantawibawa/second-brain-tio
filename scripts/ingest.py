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

    append_audit_log("INGEST", str(target_file.relative_to(REPO_ROOT)), f"Ingested {file_path.name} to {target_rel_folder}")
    return True

def append_audit_log(op_type: str, target: str, description: str):
    """Appends an entry to log.md in accordance with agents.md."""
    log_file = REPO_ROOT / "log.md"
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    entry_line = f"| {now_str} | {op_type} | `{target}` | {description} |\n"
    
    if not log_file.exists():
        log_file.write_text("# System Audit & Compounding Knowledge Log\n\n| Timestamp | Tipe Operasi | Target File / Entitas | Deskripsi Ringkas Tindakan |\n| :--- | :--- | :--- | :--- |\n", encoding="utf-8")
    
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(entry_line)
    print(f"[+] Appended audit record to log.md ({op_type})")

def update_index_catalog(topic_title: str, topic_slug: str, category: str = "Konsep"):
    """Adds a wiki concept to index.md if not already present."""
    index_file = REPO_ROOT / "index.md"
    if not index_file.exists():
        return
        
    content = index_file.read_text(encoding="utf-8")
    entry_link = f"[[{topic_slug}|{topic_title}]]"
    if entry_link in content or f"[[{topic_slug}]]" in content:
        return

    # Append under section 1
    target_section = "## 1. Konsep & Arsitektur Sistem (`wiki/`)"
    if target_section in content:
        replacement = f"{target_section}\n- {entry_link} (`{datetime.now().strftime('%Y-%m-%d')}`)"
        content = content.replace(target_section, replacement, 1)
        index_file.write_text(content, encoding="utf-8")
        print(f"[+] Updated index.md with wiki concept: {entry_link}")

def parse_raw_metadata(raw_content: str, default_title: str) -> dict:
    """
    Parses metadata frontmatter (YAML or header-style) from a raw markdown file.
    Ensures Title, Source URL, Channel/Author, and Ingest Date are extracted cleanly.
    """
    now_str = datetime.now().strftime("%Y-%m-%d")
    meta = {
        "title": default_title,
        "source_url": "",
        "author": "Ingested via Second Brain",
        "ingest_date": now_str,
        "body": raw_content
    }

    # 1. Check for YAML frontmatter
    yaml_match = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n(.*)$", raw_content, re.DOTALL)
    if yaml_match:
        yaml_text = yaml_match.group(1)
        body = yaml_match.group(2)
        meta["body"] = body.strip()
        for line in yaml_text.splitlines():
            line = line.strip()
            if not line or line.startswith("#") or ":" not in line:
                continue
            k, v = line.split(":", 1)
            k = k.strip().lower()
            v = v.strip().strip("\"'")
            if k in ("title",):
                meta["title"] = v
            elif k in ("source_url", "source", "url"):
                meta["source_url"] = v
            elif k in ("author", "channel", "creator", "speaker"):
                meta["author"] = v
            elif k in ("ingest_date", "date"):
                meta["ingest_date"] = v
        return meta

    # 2. Line-based header parsing (Title: ..., Source: ..., Author: ..., Channel: ...)
    lines = raw_content.splitlines()
    body_lines = []
    header_mode = True
    for line in lines:
        stripped = line.strip()
        if header_mode and stripped:
            lower = stripped.lower()
            if lower.startswith("title:"):
                meta["title"] = stripped.split(":", 1)[1].strip().strip("\"'")
                continue
            elif lower.startswith("source:") or lower.startswith("source url:") or lower.startswith("url:"):
                meta["source_url"] = stripped.split(":", 1)[1].strip().strip("\"'")
                continue
            elif lower.startswith("author:") or lower.startswith("channel:") or lower.startswith("speaker:"):
                meta["author"] = stripped.split(":", 1)[1].strip().strip("\"'")
                continue
            elif lower.startswith("date:") or lower.startswith("ingest date:"):
                meta["ingest_date"] = stripped.split(":", 1)[1].strip().strip("\"'")
                continue
            else:
                header_mode = False
                body_lines.append(line)
        else:
            if stripped or body_lines:
                body_lines.append(line)

    meta["body"] = "\n".join(body_lines).strip()
    return meta

def register_crm_profile(name: str, role: str, org: str, related_topic: str):
    """Creates a CRM profile and registers in crm/index.md adhering to agents.md PROTOKOL 4."""
    clean_name = name.strip()
    file_name = f"{clean_name.replace(' ', '-')}.md"
    crm_file = REPO_ROOT / "crm" / file_name
    now_str = datetime.now().strftime("%Y-%m-%d")
    
    if not crm_file.exists():
        content = f"""---
name: "{clean_name}"
role: "{role}"
organization: "{org}"
interaction_last_date: {now_str}
tags:
  - crm
  - expert
links:
  - "{related_topic}"
---

# {clean_name}

## 1. Bio Singkat & Konteks Relasi
Profil kontak yang diidentifikasi dari transkrip atau sumber pengetahuan vault.

## 2. Topik & Proyek Terkait (`wiki/` & `in_motion/`)
- {related_topic}

## 3. Log Interaksi & Keputusan Penting
- **{now_str}**: Dicatat secara otonom dari proses ingest `raw/`.
"""
        crm_file.write_text(content, encoding="utf-8")
        print(f"[+] Created CRM profile: {crm_file.relative_to(REPO_ROOT)}")

        # Update crm/index.md
        crm_index = REPO_ROOT / "crm" / "index.md"
        if crm_index.exists():
            idx_text = crm_index.read_text(encoding="utf-8")
            new_row = f"| {clean_name} | [[crm/{clean_name.replace(' ', '-')}|{clean_name}]] | {role} | {related_topic} |\n"
            if "| _Belum ada kontak_" in idx_text:
                idx_text = idx_text.replace("| _Belum ada kontak_ | _crm/[Nama-Lengkap].md_ | _Profil baru akan ditambahkan otomatis_ | _[[topik]]_ |\n", "")
            if f"| {clean_name} |" not in idx_text:
                idx_text += new_row
                crm_index.write_text(idx_text, encoding="utf-8")
                print(f"[+] Registered {clean_name} in crm/index.md")

        append_audit_log("CRM", f"crm/{file_name}", f"Registered {clean_name} profile from raw source")

def ingest_raw_to_wiki(file_path: Path, dry_run: bool = False) -> bool:
    """Ingests a file from raw/ into wiki/ adhering strictly to agents.md PROTOKOL 1."""
    if not file_path.exists() or file_path.is_dir():
        return False
        
    print(f"\n[*] [PROTOKOL 1 INGEST] Processing raw clip: {file_path.name} ...")
    raw_content = file_path.read_text(encoding="utf-8")
    if not raw_content.strip():
        return False

    now_str = datetime.now().strftime("%Y-%m-%d")
    clean_stem = slugify(file_path.stem)
    default_title = file_path.stem.replace("-", " ").title()
    
    # 1. Extract metadata from raw content
    meta = parse_raw_metadata(raw_content, default_title)

    # 2. Extract knowledge using AI engine
    try:
        import ai_engine
        data, used_model = ai_engine.parse_text_with_ai(meta["body"] if meta["body"] else raw_content, file_path.name)
        print(f"[*] Processed using AI model: {used_model}")
    except Exception as e:
        print(f"[!] AI parsing fallback ({e}).")
        data = local_heuristic_parse(meta["body"] if meta["body"] else raw_content, file_path.name)

    title = meta["title"] if meta["title"] and meta["title"] != default_title else data.get("title", default_title)
    slug = data.get("slug", clean_stem)
    source_url = meta.get("source_url", "")
    author = meta.get("author", "Ingested via Second Brain")
    ingest_date = meta.get("ingest_date", now_str)
    source_processed_path = f"raw/processed/{file_path.name}"

    # 3. Ensure raw source file has clean YAML frontmatter
    standard_raw_content = f"""---
title: "{title}"
source_url: "{source_url}"
author: "{author}"
ingest_date: {ingest_date}
---

{meta['body']}
"""
    if not dry_run:
        file_path.write_text(standard_raw_content, encoding="utf-8")

    # 4. Process CRM contact if author or key entities represent individuals
    wiki_links = [f"[[{source_processed_path}]]"]
    crm_entities = []
    
    if author and author not in ("Ingested via Second Brain", "Unknown", ""):
        # Check if author name is a person (contains space and not a bot/organization)
        if len(author.split()) >= 2 and not any(k in author.lower() for k in ["channel", "team", "inc", "ai", "bot", "system", "ingest", "gateway"]):
            crm_name = author.strip()
            crm_file = REPO_ROOT / "crm" / f"{crm_name.replace(' ', '-')}.md"
            if not crm_file.exists():
                register_crm_profile(crm_name, "Subject Matter Expert / Author", "", f"[[{slug}]]")
            crm_entities.append(crm_name)
            wiki_links.append(f"[[crm/{crm_name.replace(' ', '-')}|{crm_name}]]")

    for entity in data.get("key_entities", []):
        clean_entity = entity.strip("[]")
        # Check if entity matches known CRM profile or person
        crm_match = REPO_ROOT / "crm" / f"{clean_entity.replace(' ', '-')}.md"
        if crm_match.exists():
            wiki_links.append(f"[[crm/{clean_entity.replace(' ', '-')}|{clean_entity}]]")
        else:
            wiki_links.append(f"[[{clean_entity}]]")

    # Deduplicate links preserving order
    seen_links = set()
    deduped_links = []
    for l in wiki_links:
        if l not in seen_links:
            seen_links.add(l)
            deduped_links.append(l)

    # 5. Build wiki page format with strict agents.md YAML frontmatter
    wiki_content = f"""---
title: "{title}"
source_title: "{file_path.name}"
source_url: "{source_url}"
author: "{author}"
ingest_date: {ingest_date}
tags:
  - wiki
  - knowledge-compilation
links:
"""
    for l in deduped_links:
        wiki_content += f'  - "{l}"\n'
    wiki_content += f"""---

# {title}

## 1. Core Synthesis & Key Insights
{chr(10).join(f"- {ci}" for ci in data.get("core_insights", ["Ide sintesis utama."]))}

---

## 2. Tools, Arsitektur & Entitas
| Entitas / Tool | Tipe | Relevansi |
| :--- | :--- | :--- |
"""
    for l in deduped_links:
        if "raw/processed" in l:
            continue
        ent_label = l.strip("[]").split("|")[-1]
        t_type = "Personal CRM" if "crm/" in l else "Wiki Concept"
        wiki_content += f"| {l} | {t_type} | Referensi silang |\n"

    wiki_content += f"""
---

## 3. Actionable Takeaways
{chr(10).join(data.get("action_items", ["- [ ] Evaluasi relevansi konsep"]))}

---

## 4. Provenance & Original Source Reference
- File Asli: `[[{source_processed_path}]]`
- Waktu Ingest: `{datetime.now().strftime("%Y-%m-%d %H:%M")}`
"""
    
    target_wiki_file = REPO_ROOT / "wiki" / f"{slug}.md"
    if dry_run:
        print(f"[DRY-RUN] Target: {target_wiki_file}")
        print(wiki_content)
        return True

    target_wiki_file.write_text(wiki_content, encoding="utf-8")
    print(f"[+] Created wiki page: {target_wiki_file.relative_to(REPO_ROOT)}")

    # Update index.md & log.md
    update_index_catalog(title, slug)
    append_audit_log("INGEST", f"wiki/{slug}.md", f"Extracted from {file_path.name} to wiki/")

    # Move source file to raw/processed/
    dest_processed = REPO_ROOT / "raw" / "processed" / file_path.name
    file_path.rename(dest_processed)
    print(f"[+] Moved source file to: {dest_processed.relative_to(REPO_ROOT)}")
    return True

def main():
    load_env()
    parser = argparse.ArgumentParser(description="Second Brain Ingest Engine (Deliverable-First & Gemini AI-powered)")
    parser.add_argument("--file", "-f", help="Path to single markdown or text file in inbox_raw/")
    parser.add_argument("--all", "-a", action="store_true", help="Process all files currently in inbox_raw/")
    parser.add_argument("--raw", "-r", action="store_true", help="Process all raw files in raw/ into wiki/ (agents.md Protocol 1)")
    parser.add_argument("--dry-run", "-d", action="store_true", help="Print result to terminal without writing or moving files")
    parser.add_argument("--keep-raw", action="store_true", help="Do not move raw files to .archive after ingest")
    parser.add_argument("--target", "-t", help="Force target subfolder (e.g. in_motion/core_work, in_motion/side_builder, lattices/mental_models)")

    args = parser.parse_args()

    if args.raw:
        raw_dir = REPO_ROOT / "raw"
        items = [f for f in raw_dir.iterdir() if f.is_file() and not f.name.startswith(".")]
        if not items:
            print("[*] raw/ is empty. No clips or transcripts to ingest.")
            return
        print(f"[*] Found {len(items)} file(s) in raw/...")
        for it in items:
            ingest_raw_to_wiki(it, dry_run=args.dry_run)
            
        # Reconcile index network map
        if not args.dry_run:
            try:
                import graph_index
                vault_data = graph_index.scan_vault()
                graph_index.build_index_md(vault_data)
                print("[+] Reconciled master index with network backlink matrix.")
            except Exception as e:
                print(f"[!] Graph index build error: {e}")

    elif args.file:
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
