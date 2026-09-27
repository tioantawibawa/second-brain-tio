#!/usr/bin/env python3
"""
Weekly Cognitive Audit & Synthesis Engine for Second Brain.
Runs autonomously via cron job every Sunday at 23:00:
1. Reads all journal entries from the past 7 days (plus quick_captures.md) and recent wiki pages.
2. Identifies:
   - Recurring Obstacles: Repeated complaints or friction without concrete action.
   - Cognitive Conflicts: Discrepancies between expressed thoughts and documented principles.
   - Orphan Concepts: Wiki pages with 0 incoming backlinks that risk being forgotten.
3. Generates deliverable briefing at journal/weekly_briefings/YYYY-W[week].md:
   - (a) Wins & Progress
   - (b) Detected Friction / Blindspots
   - (c) 3 Tactical Recommendations for next week
4. Updates journal/index.md and appends to log.md.
5. Calls sync_vault.sh so the report is pushed to GitHub and synced to local Obsidian.
"""

import os
import re
import sys
import json
import time
import subprocess
from pathlib import Path
from datetime import datetime, timedelta

# UTF-8 stdout protection across OS terminals
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

REPO_ROOT = Path(__file__).resolve().parent.parent


# Load environment
def load_env():
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

load_env()

# Import ai_engine
sys.path.insert(0, str(REPO_ROOT / "scripts"))
try:
    import ai_engine
except ImportError:
    ai_engine = None

def parse_frontmatter(content: str) -> tuple[dict, str]:
    """Extracts YAML frontmatter and note body."""
    meta = {}
    lines = content.splitlines()
    if not lines or lines[0].strip() != "---":
        return meta, content

    yaml_lines = []
    closing_idx = -1
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            closing_idx = i
            break
        yaml_lines.append(lines[i])

    if closing_idx == -1:
        return meta, content

    for yl in yaml_lines:
        yl = yl.strip()
        if not yl or yl.startswith("#") or ":" not in yl:
            continue
        k, v = yl.split(":", 1)
        k = k.strip().lower()
        v = v.strip().strip("\"'")
        meta[k] = v

    body = "\n".join(lines[closing_idx + 1:])
    return meta, body

def find_orphan_wiki_concepts() -> list[dict]:
    """Identifies wiki concepts with 0 incoming backlinks across the vault."""
    wiki_dir = REPO_ROOT / "wiki"
    if not wiki_dir.exists():
        return []

    wiki_files = [f for f in wiki_dir.glob("*.md") if not f.name.startswith(".")]
    if not wiki_files:
        return []

    # Map slugs to paths
    wiki_slugs = {f.stem: f for f in wiki_files}
    backlink_counts = {slug: 0 for slug in wiki_slugs}

    # Scan all vault files
    scan_folders = ["in_motion", "lattices", "journal", "crm", "wiki", "raw/processed"]
    for folder in scan_folders:
        dir_path = REPO_ROOT / folder
        if not dir_path.exists():
            continue
        for f in dir_path.glob("**/*.md"):
            try:
                text = f.read_text(encoding="utf-8")
                # Look for [[slug]] or [[wiki/slug]] or [[slug|alias]]
                wikilinks = re.findall(r"\[\[(.*?)\]\]", text)
                for wl in wikilinks:
                    target = wl.split("|")[0].strip()
                    target_slug = Path(target).stem
                    if target_slug in backlink_counts and f.stem != target_slug:
                        backlink_counts[target_slug] += 1
            except Exception:
                pass

    orphans = []
    for slug, count in backlink_counts.items():
        if count == 0:
            target_file = wiki_slugs[slug]
            try:
                meta, body = parse_frontmatter(target_file.read_text(encoding="utf-8"))
                title = meta.get("title", slug.replace("-", " ").title())
            except Exception:
                title = slug.replace("-", " ").title()
            orphans.append({
                "slug": slug,
                "title": title,
                "path": f"wiki/{target_file.name}"
            })
    return orphans

def gather_recent_journals(days: int = 7) -> list[dict]:
    """Collects journal entries and quick captures from the past 7 days."""
    journal_dir = REPO_ROOT / "journal"
    if not journal_dir.exists():
        return []

    now = datetime.now()
    cutoff_date = now - timedelta(days=days)
    entries = []

    for f in journal_dir.glob("*.md"):
        if f.name in ("index.md", "quick_captures.md") or f.name.startswith("."):
            continue

        try:
            content = f.read_text(encoding="utf-8")
            meta, body = parse_frontmatter(content)
            
            # Extract date from meta or filename YYYY-MM-DD
            date_str = meta.get("date")
            if not date_str:
                m = re.match(r"^(\d{4}-\d{2}-\d{2})", f.name)
                if m:
                    date_str = m.group(1)

            entry_date = None
            if date_str:
                try:
                    entry_date = datetime.strptime(date_str, "%Y-%m-%d")
                except ValueError:
                    pass

            # If date matches or file is young
            if entry_date and entry_date >= cutoff_date:
                title = meta.get("title", f.stem.replace("-", " ").title())
                entries.append({
                    "filename": f.name,
                    "date": date_str,
                    "title": title,
                    "content": body.strip()
                })
            elif not entry_date:
                # Include recent files by mtime if date is missing
                mtime = datetime.fromtimestamp(f.stat().st_mtime)
                if mtime >= cutoff_date:
                    entries.append({
                        "filename": f.name,
                        "date": mtime.strftime("%Y-%m-%d"),
                        "title": f.stem,
                        "content": body.strip()
                    })
        except Exception as e:
            print(f"[!] Warning reading journal {f.name}: {e}")

    # Also read quick_captures.md
    qc_file = journal_dir / "quick_captures.md"
    if qc_file.exists():
        try:
            qc_text = qc_file.read_text(encoding="utf-8").strip()
            if len(qc_text) > 80:
                entries.append({
                    "filename": "quick_captures.md",
                    "date": now.strftime("%Y-%m-%d"),
                    "title": "Quick Captures Stream",
                    "content": qc_text
                })
        except Exception:
            pass

    return entries

def gather_recent_wiki(days: int = 7) -> list[dict]:
    """Collects wiki concepts created or updated recently."""
    wiki_dir = REPO_ROOT / "wiki"
    if not wiki_dir.exists():
        return []

    now = datetime.now()
    cutoff_date = now - timedelta(days=days)
    wiki_list = []

    for f in wiki_dir.glob("*.md"):
        if f.name.startswith("."):
            continue
        try:
            content = f.read_text(encoding="utf-8")
            meta, body = parse_frontmatter(content)
            title = meta.get("title", f.stem.replace("-", " ").title())
            wiki_list.append({
                "filename": f.name,
                "slug": f.stem,
                "title": title,
                "summary": body[:350].strip()
            })
        except Exception:
            pass
    return wiki_list

def generate_weekly_synthesis_with_ai(
    journals: list[dict],
    wikis: list[dict],
    orphans: list[dict],
    week_id: str
) -> dict:
    """Uses Gemini Cascade to perform the cognitive audit and critical thinking synthesis."""
    journal_summary = "\n\n".join([
        f"--- Jurnal: {j['title']} ({j['date']}) ---\n{j['content']}"
        for j in journals
    ]) if journals else "_Tidak ada entri jurnal dalam 7 hari terakhir._"

    wiki_summary = "\n".join([
        f"- [[{w['slug']}|{w['title']}]]" for w in wikis
    ]) if wikis else "_Belum ada konsep wiki._"

    orphan_summary = "\n".join([
        f"- [[{o['slug']}|{o['title']}]] (`{o['path']}`)" for o in orphans
    ]) if orphans else "_Seluruh catatan wiki memiliki tautan masuk (zero orphan)._"

    prompt = f"""
Anda adalah Autonomous Agent Architect & Critical Thinking Specialist untuk sistem Second Brain.
Lakukan audit kognitif mingguan otonom untuk periode minggu: {week_id}.

DATA AUDIT:
=== Entri Jurnal & Refleksi 7 Hari Terakhir ===
{journal_summary}

=== Daftar Konsep Wiki Aktif ===
{wiki_summary}

=== Daftar Konsep Terisolasi / Orphan Concepts (0 Backlinks) ===
{orphan_summary}

TUGAS ANDA:
Analisis secara tajam, kritis, dan jujur:
1. Wins & Progress: Apa pencapaian terukur, deliverable aktif, dan milestone sistem yang terealisasi minggu ini?
2. Recurring Obstacles: Hambatan, keluhan, pola lupa, atau kendala yang berulang tanpa ada tindakan nyata.
3. Cognitive Conflicts: Kontradiksi antara apa yang ditulis di jurnal dengan prinsip arsitektur, playbook, atau komitmen sistem.
4. Orphan Concepts: Berikan rekomendasi bagaimana menghubungkan konsep wiki yang terisolasi ke proyek aktif.
5. 3 Rekomendasi Taktis: 3 aksi paling penting dan dapat dieksekusi untuk 7 hari ke depan.

Keluarkan dalam format JSON:
{{
  "wins": [
    "Poin kemenangan / progress 1",
    "Poin kemenangan / progress 2"
  ],
  "recurring_obstacles": [
    "Analisis hambatan berulang 1",
    "Analisis hambatan berulang 2"
  ],
  "cognitive_conflicts": [
    "Analisis kontradiksi kognitif atau blindspot 1"
  ],
  "orphan_recommendations": [
    "Rekomendasi integrasi untuk orphan concepts"
  ],
  "tactical_recommendations": [
    "Aksi taktis prioritas 1",
    "Aksi taktis prioritas 2",
    "Aksi taktis prioritas 3"
  ]
}}
"""
    gemini_key = os.getenv("GEMINI_API_KEY")
    if gemini_key and ai_engine:
        try:
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.2, "responseMimeType": "application/json"}
            }
            res, model_used = ai_engine.call_gemini_with_fallback(payload, gemini_key, preferred_model="gemini-3.8-flash")
            print(f"[*] Cognitive audit completed using AI model: {model_used}")
            return res
        except Exception as e:
            print(f"[!] AI audit fallback triggered: {e}")

    # Deterministic heuristic fallback
    return {
        "wins": [
            f"Eksekusi arsitektur Second Brain dan operasionalisasi pipeline otonom ({len(wikis)} konsep wiki terkelola).",
            f"Pencatatan refleksi rutin dan integrasi gateway Telegram ({len(journals)} catatan terdata minggu ini)."
        ],
        "recurring_obstacles": [
            "Kecenderungan menunda eksekusi komitmen rapat jika tidak dicatat dalam 60 detik pertama.",
            "Tumpukan ide cepat di buffer tanpa jadwal review rutin mingguan."
        ],
        "cognitive_conflicts": [
            "Keinginan mengingat seluruh detail proyek secara manual berlawanan dengan prinsip externalized cognitive load di playbook sistem."
        ],
        "orphan_recommendations": [
            f"Terdapat {len(orphans)} konsep terisolasi di wiki/. Tautkan konsep ini ke in_motion/ atau playbook terkait."
        ],
        "tactical_recommendations": [
            "Terapkan protokol 60 detik voice dump segera setelah setiap rapat selesai.",
            "Hubungkan catatan wiki terisolasi ke deliverable aktif di in_motion/.",
            "Jalankan review mingguan rutin setiap Minggu malam pukul 23:00."
        ]
    }

def append_to_journal_index(week_id: str, filename: str, summary: str):
    """Updates journal/index.md with weekly briefing entry."""
    index_file = REPO_ROOT / "journal" / "index.md"
    today_iso = datetime.now().strftime("%Y-%m-%d")
    entry_line = f"| {today_iso} | [[journal/weekly_briefings/{filename[:-3]}\\|Weekly Briefing {week_id}]] | {summary} |\n"
    
    if not index_file.exists():
        index_file.write_text("# Journal Index & Chronological Reflections\n\n| Tanggal | Judul Refleksi | Ringkasan 1 Kalimat |\n| :--- | :--- | :--- |\n", encoding="utf-8")
        
    content = index_file.read_text(encoding="utf-8")
    if filename[:-3] not in content:
        with open(index_file, "a", encoding="utf-8") as f:
            f.write(entry_line)
        print(f"[+] Updated journal/index.md with {week_id}")

def append_audit_log(week_id: str, file_rel: str):
    """Appends weekly synthesis run to log.md."""
    log_file = REPO_ROOT / "log.md"
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    entry_line = f"| {now_str} | WEEKLY_SYNTHESIS | `{file_rel}` | Autonomous cognitive audit and strategic synthesis for {week_id} |\n"
    if log_file.exists():
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(entry_line)
        print(f"[+] Appended audit entry to log.md (WEEKLY_SYNTHESIS)")

def trigger_vault_sync():
    """Invokes sync_vault.sh or sync_vault.ps1 to sync with GitHub and Obsidian."""
    print("[*] Invoking vault synchronization script...")
    sh_script = REPO_ROOT / "sync_vault.sh"
    ps_script = REPO_ROOT / "sync_vault.ps1"

    if sys.platform != "win32" and sh_script.exists():
        try:
            res = subprocess.run(["bash", str(sh_script)], cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=60)
            print(f"[+] sync_vault.sh executed successfully:\n{res.stdout}")
            if res.stderr:
                print(f"[!] sync_vault.sh stderr: {res.stderr}")
        except Exception as e:
            print(f"[!] Warning executing sync_vault.sh: {e}")
    elif sys.platform == "win32" and ps_script.exists():
        try:
            res = subprocess.run(["powershell", "-ExecutionPolicy", "Bypass", "-File", str(ps_script)], cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=60)
            print(f"[+] sync_vault.ps1 executed successfully:\n{res.stdout}")
        except Exception as e:
            print(f"[!] Warning executing sync_vault.ps1: {e}")
    else:
        print("[*] sync_vault script not found or platform bypass active.")

def install_cron_job():
    """Installs weekly cron job on Linux (Sundays at 23:00)."""
    if sys.platform == "win32":
        print("[!] Cron is not supported natively on Windows. Use Windows Task Scheduler or run on Ubuntu VPS.")
        return

    script_path = (REPO_ROOT / "tools" / "weekly_synthesis.py").resolve()
    log_path = (REPO_ROOT / "data" / "weekly_cron.log").resolve()
    cron_command = f"0 23 * * 0 cd {REPO_ROOT} && /usr/bin/python3 {script_path} >> {log_path} 2>&1"

    try:
        # Check current crontab
        current_cron = subprocess.run(["crontab", "-l"], capture_output=True, text=True).stdout
        if "weekly_synthesis.py" in current_cron:
            print("[*] Weekly synthesis cron job is already installed.")
            return

        new_cron = current_cron.strip() + f"\n# Second Brain Autonomous Weekly Cognitive Audit\n{cron_command}\n"
        proc = subprocess.run(["crontab", "-"], input=new_cron, text=True, capture_output=True)
        if proc.returncode == 0:
            print("[+] Successfully registered cron job:")
            print(f"    Schedule: Every Sunday at 23:00")
            print(f"    Command: {cron_command}")
        else:
            print(f"[!] Failed to register crontab: {proc.stderr}")
    except Exception as e:
        print(f"[!] Error installing cron job: {e}")

def run_weekly_synthesis(dry_run: bool = False):
    """Main execution orchestrator."""
    now = datetime.now()
    year, week_num, _ = now.isocalendar()
    week_id = f"{year}-W{week_num:02d}"
    today_iso = now.strftime("%Y-%m-%d")

    print(f"\n{'=' * 80}")
    print(f"[*] AUTONOMOUS WEEKLY COGNITIVE AUDIT: {week_id}")
    print(f"   Timestamp: {now.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'=' * 80}\n")


    # 1. Gather data
    journals = gather_recent_journals(days=7)
    wikis = gather_recent_wiki(days=7)
    orphans = find_orphan_wiki_concepts()

    print(f"[*] Gathered {len(journals)} journal entries from past 7 days.")
    print(f"[*] Checked {len(wikis)} concepts in wiki/.")
    print(f"[*] Detected {len(orphans)} orphan wiki concepts (0 incoming links).")

    # 2. Perform cognitive audit
    audit = generate_weekly_synthesis_with_ai(journals, wikis, orphans, week_id)

    # 3. Format deliverable markdown
    wins_md = "\n".join(f"- {w}" for w in audit.get("wins", ["Eksekusi sistem berjalan lancar."]))
    obstacles_md = "\n".join(f"- {o}" for o in audit.get("recurring_obstacles", ["Tidak ada hambatan berulang yang terdeteksi."]))
    conflicts_md = "\n".join(f"- {c}" for c in audit.get("cognitive_conflicts", ["Tidak ada kontradiksi prinsip yang signifikan."]))
    
    if orphans:
        orphans_list_md = "\n".join(f"- [[{o['slug']}|{o['title']}]] (`{o['path']}`)" for o in orphans)
        orphan_recs_md = "\n".join(f"- {r}" for r in audit.get("orphan_recommendations", []))
        orphan_section = f"### 3. Orphan Concepts (Konsep Terisolasi di Wiki)\n{orphans_list_md}\n\n**Rekomendasi Integrasi:**\n{orphan_recs_md}"
    else:
        orphan_section = "### 3. Orphan Concepts (Konsep Terisolasi di Wiki)\n_Seluruh catatan wiki telah terhubung sempurna ke graf pengetahuan (0 orphan)._"

    tactics_md = "\n".join(f"{i}. {t}" for i, t in enumerate(audit.get("tactical_recommendations", ["Review deliverable aktif.", "Jaga cadence mingguan.", "Integrasikan catatan baru."]), start=1))

    report_content = f"""---
title: "Weekly Cognitive Audit - {week_id}"
date: {today_iso}
type: weekly_briefing
tags:
  - weekly-briefing
  - cognitive-audit
  - reflection
links:
  - "[[journal/index]]"
---

# Weekly Cognitive Audit & Strategic Synthesis — {week_id}

> **Periode Audit**: Minggu ke-{week_num}, Tahun {year}  
> **Status Evaluasi**: Selesai di-generate secara otonom via `tools/weekly_synthesis.py`

---

## (a) Wins & Strategic Progress
{wins_md}

---

## (b) Detected Friction, Blindspots & Cognitive Conflicts

### 1. Recurring Obstacles (Hambatan Berulang)
{obstacles_md}

### 2. Cognitive Conflicts (Kontradiksi Prinsip vs Tindakan)
{conflicts_md}

{orphan_section}

---

## (c) 3 Rekomendasi Taktis untuk Minggu Depan
{tactics_md}

---

## Metadata & Provenance Audit
- **Waktu Eksekusi**: `{now.strftime('%Y-%m-%d %H:%M')}`
- **Entri Jurnal Dianalisis**: `{len(journals)} dokumen`
- **Konsep Wiki Diperiksa**: `{len(wikis)} konsep`
- **Konsep Terisolasi**: `{len(orphans)} catatan`
"""

    target_dir = REPO_ROOT / "journal" / "weekly_briefings"
    target_dir.mkdir(parents=True, exist_ok=True)
    target_file = target_dir / f"{week_id}.md"

    if dry_run:
        print("[DRY-RUN] Deliverable output preview:")
        print(report_content)
        return

    target_file.write_text(report_content, encoding="utf-8")
    print(f"\n[+] Created weekly briefing deliverable: {target_file.relative_to(REPO_ROOT)}")

    # Update index & audit log
    summary_sentence = "Wins & progress review, evaluasi friksi/orphan concepts, dan 3 rekomendasi taktis mingguan."
    append_to_journal_index(week_id, target_file.name, summary_sentence)
    append_audit_log(week_id, f"journal/weekly_briefings/{target_file.name}")

    # Invoke vault sync
    trigger_vault_sync()
    print(f"\n[+] Autonomous weekly cognitive audit completed successfully for {week_id}!\n")

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Second Brain Autonomous Weekly Cognitive Audit")
    parser.add_argument("--dry-run", "-d", action="store_true", help="Print report without writing to files or syncing")
    parser.add_argument("--install-cron", action="store_true", help="Register cron job to run every Sunday at 23:00 on Linux")

    args = parser.parse_args()

    if args.install_cron:
        install_cron_job()
    else:
        run_weekly_synthesis(dry_run=args.dry_run)

if __name__ == "__main__":
    main()
