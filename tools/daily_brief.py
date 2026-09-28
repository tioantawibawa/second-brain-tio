#!/usr/bin/env python3
"""
Autonomous Daily Executive Morning Pulse & Serendipity Digest.
Runs on-demand or as a daily morning trigger:
1. Gathers active workstreams from in_motion/ (core_work & side_builder).
2. Extracts pending action items (- [ ]) from active deliverables.
3. Retrieves quick thoughts captured in the last 24-48 hours.
4. Surfaces 1 random/under-visited concept from wiki/ (Serendipity Spark).
5. Delivers a high-leverage executive morning briefing via CLI & Telegram (/brief).
"""

import os
import re
import sys
import random
from pathlib import Path
from datetime import datetime, timedelta

# UTF-8 stdout protection
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

REPO_ROOT = Path(__file__).resolve().parent.parent

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

def get_active_workstreams() -> list[dict]:
    """Finds active deliverables in in_motion/."""
    im_dir = REPO_ROOT / "in_motion"
    if not im_dir.exists():
        return []
    
    streams = []
    for f in im_dir.glob("**/*.md"):
        if f.name in ("index.md", "INDEX.md", "README.md"):
            continue
        try:
            content = f.read_text(encoding="utf-8")
            title = f.stem.replace("-", " ").replace("_", " ").title()
            m = re.search(r"^title:\s*[\"']?(.*?)[\"']?$", content[:500], re.MULTILINE)
            if m:
                title = m.group(1).strip()
            
            # Check stream category
            stream_name = "Core Work" if "core_work" in f.parts else ("Side Builder" if "side_builder" in f.parts else "In Motion")
            streams.append({
                "title": title,
                "file_path": f.relative_to(REPO_ROOT).as_posix(),
                "slug": f.stem,
                "stream": stream_name,
                "mtime": f.stat().st_mtime
            })
        except Exception:
            pass
            
    streams.sort(key=lambda x: x["mtime"], reverse=True)
    return streams[:5]

def get_recent_captures(hours: int = 48) -> list[str]:
    """Extracts recent quick thoughts from journal/quick_captures.md."""
    qc_file = REPO_ROOT / "journal" / "quick_captures.md"
    if not qc_file.exists():
        return []
    
    try:
        content = qc_file.read_text(encoding="utf-8")
        lines = [line.strip() for line in content.splitlines() if line.strip().startswith("- ")]
        return lines[-4:]  # Last 4 quick thoughts
    except Exception:
        return []

def get_pending_action_items() -> list[dict]:
    """Finds unchecked checkboxes (- [ ]) in active documents."""
    tasks = []
    dirs = [REPO_ROOT / "in_motion", REPO_ROOT / "system_triggers"]
    for d in dirs:
        if not d.exists():
            continue
        for f in d.glob("**/*.md"):
            try:
                for line in f.read_text(encoding="utf-8").splitlines():
                    clean = line.strip()
                    if clean.startswith("- [ ]") and len(clean) > 6:
                        task_text = clean[5:].strip()
                        tasks.append({
                            "task": task_text,
                            "source": f.name
                        })
                        if len(tasks) >= 4:
                            return tasks
            except Exception:
                pass
    return tasks

def get_serendipity_spark() -> dict:
    """Surfaces 1 concept from wiki/ to activate serendipitous knowledge recall."""
    wiki_dir = REPO_ROOT / "wiki"
    if not wiki_dir.exists():
        return None
    
    candidates = []
    for f in wiki_dir.glob("*.md"):
        if f.name in ("index.md", "README.md", "INDEX.md"):
            continue
        candidates.append(f)
        
    if not candidates:
        return None
        
    chosen = random.choice(candidates)
    try:
        txt = chosen.read_text(encoding="utf-8")
        title = chosen.stem.replace("-", " ").title()
        m = re.search(r"^title:\s*[\"']?(.*?)[\"']?$", txt[:500], re.MULTILINE)
        if m:
            title = m.group(1).strip()
            
        # Extract snippet after frontmatter
        body = re.sub(r"^---[\s\S]*?---\n*", "", txt).strip()
        lines = [l.strip() for l in body.splitlines() if l.strip() and not l.strip().startswith("#")]
        snippet = " ".join(lines[:2]) if lines else "Konsep penting di wiki Anda."
        
        return {
            "title": title,
            "file_path": chosen.relative_to(REPO_ROOT).as_posix(),
            "slug": chosen.stem,
            "snippet": snippet[:150]
        }
    except Exception:
        return None

def build_morning_briefing() -> str:
    """Constructs the daily morning executive pulse report."""
    now = datetime.now()
    date_display = now.strftime("%A, %d %B %Y")
    
    workstreams = get_active_workstreams()
    recent_qc = get_recent_captures()
    pending_tasks = get_pending_action_items()
    spark = get_serendipity_spark()
    
    # 1. Workstreams
    ws_text = ""
    if workstreams:
        for ws in workstreams[:3]:
            clean_slug = re.sub(r"[^a-zA-Z0-9_]", "_", ws["slug"])
            ws_text += f"• *{ws['title']}* (`{ws['stream']}`)\n  👉 /read_{clean_slug}\n"
    else:
        ws_text = "• _Tidak ada deliverable aktif. In Motion bersih._\n"

    # 2. Pending Tasks
    task_text = ""
    if pending_tasks:
        for t in pending_tasks[:3]:
            task_text += f"▫️ {t['task']} _({t['source']})_\n"
    else:
        task_text = "▫️ _Semua task checklist selesai._\n"

    # 3. Recent Quick Thoughts
    qc_text = ""
    if recent_qc:
        for q in recent_qc[-3:]:
            qc_text += f"💬 _{q}_\n"
    else:
        qc_text = "_Belum ada catatan ide kilat dalam 24 jam terakhir._\n"

    # 4. Serendipity Spark
    spark_text = ""
    if spark:
        clean_slug = re.sub(r"[^a-zA-Z0-9_]", "_", spark["slug"])
        spark_text = (
            f"💡 *Serendipity Concept of the Day:*\n"
            f"🔬 *{spark['title']}*\n"
            f"_{spark['snippet']}..._\n"
            f"📖 Refleksikan kembali: /read_{clean_slug}\n"
        )

    briefing = (
        f"🌅 *SECOND BRAIN MORNING EXECUTIVE PULSE*\n"
        f"📅 `{date_display}`\n\n"
        f"🎯 *Active Workstreams (Fokus Utama):*\n"
        f"{ws_text}\n"
        f"⚠️ *Pending Commitments & Action Items:*\n"
        f"{task_text}\n"
        f"📝 *Tangkapan Cepat Terkini:*\n"
        f"{qc_text}\n"
        f"{spark_text}\n"
        f"⚡ *Quick Action:* Ketik `/ingest` untuk memproses inbox atau `/search <topik>` untuk mulai bekerja."
    )
    return briefing

def main():
    print(build_morning_briefing())

if __name__ == "__main__":
    main()
