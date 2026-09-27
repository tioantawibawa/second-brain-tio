#!/usr/bin/env python3
"""
Graph Indexer & Lightweight Local Semantic Search Engine.
Features:
1. Rebuilds INDEX.md with bidirectional link analysis (outward links, backlinks, dangling links).
2. In-memory BM25 / TF-IDF semantic search CLI with relevance scoring and context excerpts.
Zero external dependencies (Pure Python 3 Standard Library).
"""

import os
import re
import math
import argparse
from pathlib import Path
from collections import defaultdict, Counter
from datetime import datetime

REPO_ROOT = Path(__file__).resolve().parent.parent

EXCLUDE_DIRS = {".git", ".obsidian", ".archive", "__pycache__", "scripts"}

def parse_frontmatter(content: str) -> tuple[dict, str]:
    """Extracts YAML frontmatter and note body."""
    meta = {}
    body = content
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            raw_yaml = parts[1]
            body = parts[2]
            for line in raw_yaml.splitlines():
                line = line.strip()
                if not line or line.startswith("#") or ":" not in line:
                    continue
                k, v = line.split(":", 1)
                k = k.strip()
                v = v.strip().strip("\"'")
                if v.startswith("[") and v.endswith("]"):
                    v = [x.strip().strip("\"'") for x in v[1:-1].split(",") if x.strip()]
                meta[k] = v
    return meta, body

def extract_wikilinks(text: str) -> list[str]:
    """Finds all [[link]] occurrences."""
    matches = re.findall(r"\[\[(.*?)\]\]", text)
    links = []
    for m in matches:
        # Handle aliases: [[link|alias]] -> link
        target = m.split("|")[0].strip()
        # Ignore template placeholders like {{TITLE}}
        if "{{" in target or "}}" in target:
            continue
        links.append(target)
    return links

def scan_vault() -> dict:
    """Scans all markdown files in the second brain vault."""
    notes = {}
    slug_to_path = {}
    
    for md_file in REPO_ROOT.glob("**/*.md"):
        # Exclude ignored dirs
        if any(ex in md_file.parts for ex in EXCLUDE_DIRS):
            continue
        if md_file.name.lower() in ["index.md", "agents.md", "log.md"]:
            continue
            
        rel_path = md_file.relative_to(REPO_ROOT).as_posix()
        slug = md_file.stem
        content = md_file.read_text(encoding="utf-8")
        meta, body = parse_frontmatter(content)
        
        # Extract title
        title = meta.get("title")
        if not title:
            h1_match = re.search(r"^#\s+(.+)$", body, re.MULTILINE)
            title = h1_match.group(1).strip() if h1_match else slug.replace("-", " ").title()
            
        links = extract_wikilinks(content)
        
        notes[rel_path] = {
            "slug": slug,
            "title": title,
            "path": rel_path,
            "meta": meta,
            "links": list(set(links)),
            "content": content,
            "body": body,
            "category": md_file.parent.relative_to(REPO_ROOT).as_posix()
        }
        slug_to_path[slug] = rel_path
        slug_to_path[rel_path] = rel_path
        if rel_path.endswith(".md"):
            slug_to_path[rel_path[:-3]] = rel_path

    # Compute backlinks and dangling links
    backlinks = defaultdict(list)
    dangling_links = defaultdict(list)
    
    for rel_path, note in notes.items():
        for link in note["links"]:
            clean_link = link.replace("\\", "").strip()
            link_stem = Path(clean_link).stem
            if clean_link in slug_to_path:
                target_path = slug_to_path[clean_link]
                backlinks[target_path].append(rel_path)
            elif link_stem in slug_to_path:
                target_path = slug_to_path[link_stem]
                backlinks[target_path].append(rel_path)
            elif clean_link in notes or f"{clean_link}.md" in notes:
                target_path = clean_link if clean_link in notes else f"{clean_link}.md"
                backlinks[target_path].append(rel_path)
            else:
                dangling_links[clean_link].append(rel_path)
                
    return {
        "notes": notes,
        "slug_to_path": slug_to_path,
        "backlinks": backlinks,
        "dangling_links": dangling_links
    }

def build_index_md(vault_data: dict) -> Path:
    """Generates the main INDEX.md network dashboard."""
    notes = vault_data["notes"]
    backlinks = vault_data["backlinks"]
    dangling_links = vault_data["dangling_links"]
    
    # Categorize notes
    core_work = []
    side_builder = []
    mental_models = []
    playbooks = []
    triggers = []
    wiki_notes = []
    crm_contacts = []
    journal_notes = []
    others = []
    
    for p, n in sorted(notes.items(), key=lambda x: x[1]["title"]):
        cat = n["category"]
        if "in_motion/core_work" in cat:
            core_work.append(n)
        elif "in_motion/side_builder" in cat:
            side_builder.append(n)
        elif "wiki" in cat:
            wiki_notes.append(n)
        elif "lattices/mental_models" in cat:
            mental_models.append(n)
        elif "lattices/playbooks" in cat:
            playbooks.append(n)
        elif "crm" in cat:
            crm_contacts.append(n)
        elif "journal" in cat:
            journal_notes.append(n)
        elif "system_triggers" in cat:
            triggers.append(n)
        else:
            others.append(n)

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    md = f"""# Knowledge Network Index & Central MOC

> Auto-generated network map & backlink connectivity matrix.
> Last updated: `{now_str}` | Total Notes: `{len(notes)}`

---

## 1. Active Workstreams (`in_motion/`)

### Core Work (Professional & Enterprise Deliverables)
"""
    if core_work:
        md += "| Deliverable | Status | Outgoing | Backlinks |\n| :--- | :--- | :--- | :--- |\n"
        for n in core_work:
            bl_count = len(backlinks.get(n["path"], []))
            out_count = len(n["links"])
            status = n["meta"].get("status", "active")
            md += f"| [[{n['slug']}\\|{n['title']}]] | `{status}` | {out_count} | {bl_count} |\n"
    else:
        md += "_Tidak ada deliverable core_work aktif saat ini._\n"

    md += "\n### Side Builder (Eksperimen AI Agent & Prototipe)\n"
    if side_builder:
        md += "| Project / Agent | Status | Outgoing | Backlinks |\n| :--- | :--- | :--- | :--- |\n"
        for n in side_builder:
            bl_count = len(backlinks.get(n["path"], []))
            out_count = len(n["links"])
            status = n["meta"].get("status", "active")
            md += f"| [[{n['slug']}\\|{n['title']}]] | `{status}` | {out_count} | {bl_count} |\n"
    else:
        md += "_Tidak ada proyek side_builder aktif saat ini._\n"

    md += """
---

## 2. Knowledge Wiki & Topic Syntheses (`wiki/`)
"""
    if wiki_notes:
        md += "| Konsep / Entitas | Outgoing | Backlinks |\n| :--- | :--- | :--- |\n"
        for n in wiki_notes:
            bl_count = len(backlinks.get(n["path"], []))
            out_count = len(n["links"])
            md += f"| [[{n['slug']}\\|{n['title']}]] | {out_count} | {bl_count} |\n"
    else:
        md += "_Belum ada konsep wiki terdaftar._\n"

    md += """
---

## 3. Structural Knowledge Lattices (`lattices/`)

### Mental Models & Frameworks
"""
    if mental_models:
        for n in mental_models:
            bl_count = len(backlinks.get(n["path"], []))
            md += f"- [[{n['slug']}\\|{n['title']}]] `({bl_count} references)`\n"
    else:
        md += "_Belum ada mental model yang didokumentasikan._\n"

    md += "\n### Engineering Playbooks & SOPs\n"
    if playbooks:
        for n in playbooks:
            bl_count = len(backlinks.get(n["path"], []))
            md += f"- [[{n['slug']}\\|{n['title']}]] `({bl_count} references)`\n"
    else:
        md += "_Belum ada playbook terdaftar._\n"

    md += """
---

## 4. Personal CRM & Key Entities (`crm/`)
"""
    if crm_contacts:
        md += "| Kontak | Jabatan / Keahlian | Outgoing | Backlinks |\n| :--- | :--- | :--- | :--- |\n"
        for n in crm_contacts:
            bl_count = len(backlinks.get(n["path"], []))
            out_count = len(n["links"])
            role = n["meta"].get("role", "Kontak")
            md += f"| [[{n['path'][:-3]}\\|{n['title']}]] | {role} | {out_count} | {bl_count} |\n"
    else:
        md += "_Belum ada profil CRM terdaftar._\n"

    md += """
---

## 5. Journal Reflections (`journal/`)
"""
    if journal_notes:
        md += "| Tanggal | Entri Jurnal | Outgoing | Backlinks |\n| :--- | :--- | :--- | :--- |\n"
        for n in sorted(journal_notes, key=lambda x: x["path"], reverse=True):
            bl_count = len(backlinks.get(n["path"], []))
            out_count = len(n["links"])
            date_str = n["meta"].get("date", n["slug"][:10])
            md += f"| `{date_str}` | [[{n['path'][:-3]}\\|{n['title']}]] | {out_count} | {bl_count} |\n"
    else:
        md += "_Belum ada entri jurnal terdaftar._\n"

    md += """
---

## 6. System Triggers & Execution Engines (`system_triggers/`)
"""
    for n in triggers:
        md += f"- [[{n['slug']}\\|{n['title']}]]\n"

    md += """
---

## 7. Dangling Links (Unrealized Ideas & Build Seeds)
> Konsep yang dirujuk dengan `[[wikilinks]]` namun belum dibuat filenya secara fisik. Gunakan ini sebagai backlog ide builder.

"""
    if dangling_links:
        md += "| Target Konsep | Dirujuk Oleh |\n| :--- | :--- |\n"
        for target, referrers in sorted(dangling_links.items(), key=lambda x: len(x[1]), reverse=True):
            refs_str = ", ".join(f"[[{Path(r).stem}]]" for r in referrers)
            md += f"| `[[{target}]]` | {refs_str} |\n"
    else:
        md += "_Seluruh link di dalam repositori telah terhubung sempurna._\n"

    index_path = REPO_ROOT / "INDEX.md"
    index_path.write_text(md, encoding="utf-8")
    index_path_lower = REPO_ROOT / "index.md"
    try:
        if index_path_lower.resolve() != index_path.resolve():
            index_path_lower.write_text(md, encoding="utf-8")
    except Exception:
        pass
    return index_path


# ================= Local BM25 Semantic Search Engine =================

def tokenize(text: str) -> list[str]:
    """Basic alphanumeric tokenizer with lowercasing."""
    return re.findall(r"\b[a-zA-Z0-9_-]{2,}\b", text.lower())

def search_vault(vault_data: dict, query: str, top_k: int = 5):
    """BM25 ranking search across all notes in vault."""
    notes = vault_data["notes"]
    query_tokens = tokenize(query)
    if not query_tokens:
        print("[!] Empty search query.")
        return

    doc_tokens = {}
    doc_lens = {}
    df = Counter()
    total_docs = len(notes)

    for path, note in notes.items():
        tokens = tokenize(f"{note['title']} {note['body']}")
        doc_tokens[path] = Counter(tokens)
        doc_lens[path] = len(tokens)
        for term in set(tokens):
            df[term] += 1

    avg_dl = sum(doc_lens.values()) / max(total_docs, 1)
    k1 = 1.5
    b = 0.75

    scores = []
    for path, note in notes.items():
        score = 0.0
        tokens_count = doc_tokens[path]
        dl = doc_lens[path]
        
        # Boost if title matches
        title_lower = note["title"].lower()
        for qt in query_tokens:
            if qt in title_lower:
                score += 5.0

        for term in query_tokens:
            if term not in tokens_count:
                continue
            tf = tokens_count[term]
            n_q = df[term]
            idf = math.log((total_docs - n_q + 0.5) / (n_q + 0.5) + 1.0)
            term_score = idf * (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * (dl / max(avg_dl, 1))))
            score += term_score

        if score > 0:
            scores.append((score, path, note))

    scores.sort(key=lambda x: x[0], reverse=True)

    print(f"\n[*] Search results for: \"{query}\" (Top {min(top_k, len(scores))} of {len(scores)} matches)")
    print("=" * 80)
    
    if not scores:
        print("[-] No matching notes found.")
        return

    for rank, (score, path, note) in enumerate(scores[:top_k], 1):
        print(f"\n[{rank}] Score: {score:.2f} | [[{note['slug']}]] - {note['title']}")
        print(f"    Path: {path} | Category: {note['category']}")
        
        # Find context excerpt
        body_lower = note["body"].lower()
        snippet = ""
        for qt in query_tokens:
            idx = body_lower.find(qt)
            if idx != -1:
                start = max(0, idx - 50)
                end = min(len(note["body"]), idx + 120)
                clean_snippet = note["body"][start:end].replace("\n", " ").strip()
                snippet = f"...{clean_snippet}..."
                break
        if not snippet:
            snippet = note["body"][:120].replace("\n", " ").strip() + "..."
        print(f"    Snippet: {snippet}")
    print("\n" + "=" * 80)

def main():
    parser = argparse.ArgumentParser(description="Second Brain Graph Indexer & Search")
    subparsers = parser.add_subparsers(dest="command", help="Sub-commands")

    # Build index command
    subparsers.add_parser("build", help="Rebuild INDEX.md with link analysis")

    # Search command
    search_parser = subparsers.add_parser("search", help="Perform BM25 semantic keyword search across notes")
    search_parser.add_argument("query", help="Search query string")
    search_parser.add_argument("--top", "-n", type=int, default=5, help="Number of results to return (default: 5)")

    args = parser.parse_args()

    vault_data = scan_vault()

    if args.command == "build" or not args.command:
        idx_path = build_index_md(vault_data)
        print(f"[+] Successfully built INDEX.md at {idx_path}")
        print(f"    - Scanned {len(vault_data['notes'])} notes")
        print(f"    - Identified {len(vault_data['dangling_links'])} dangling seed links")
    elif args.command == "search":
        search_vault(vault_data, args.query, top_k=args.top)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
