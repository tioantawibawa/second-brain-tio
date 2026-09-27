#!/usr/bin/env python3
"""
Telegram Ingest Bot Daemon for Second Brain.
Captures fast mobile inputs directly into Second Brain directories:
1. Voice Notes / Audio: Transcribed via Whisper / AI Cascade -> raw/voice_dump_YYYYMMDD_HHMMSS.md (#voice-dump)
2. Web / YouTube Links: Auto-extracts title -> raw/web_YYYYMMDD_HHMMSS_[slug].md
3. Short Thoughts: Appended directly to journal/quick_captures.md with timestamp
4. Strict Security: Whitelisted Telegram User ID only
5. Architecture: Supports python-telegram-bot (v20+) with automatic resilient fallback
"""

import os
import re
import sys
import json
import time
import html
import logging
import urllib.parse
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path

# Setup logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger("telegram_ingest_bot")

REPO_ROOT = Path(__file__).resolve().parent.parent

def load_env():
    """Loads environment variables from .env."""
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

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
ALLOWED_USER_ID = os.getenv("TELEGRAM_ALLOWED_USER_ID", "").strip()
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash").strip()

def slugify(text: str) -> str:
    """Generates clean slug from title."""
    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    return text.strip("-")[:40]

# ================= 1. URL & Title Extraction =================

def extract_url_title(url: str) -> str:
    """Extracts webpage title from YouTube oEmbed or HTML <title>."""
    # YouTube oEmbed API
    if any(k in url.lower() for k in ["youtube.com", "youtu.be"]):
        try:
            oembed_url = f"https://www.youtube.com/oembed?url={urllib.parse.quote(url)}&format=json"
            req = urllib.request.Request(oembed_url, headers={"User-Agent": "SecondBrainBot/1.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data.get("title", "YouTube Video")
        except Exception as e:
            logger.debug(f"YouTube oEmbed fallback: {e}")

    # Generic Webpage HTML scraping
    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw_bytes = resp.read(150000)
            content = raw_bytes.decode("utf-8", errors="ignore")
            
            # 1. Check og:title
            og_match = re.search(r'<meta[^>]*property=["\']og:title["\'][^>]*content=["\']([^"\']+)["\']', content, re.IGNORECASE)
            if og_match:
                return html.unescape(og_match.group(1).strip())
                
            # 2. Check standard <title>
            title_match = re.search(r"<title[^>]*>(.*?)</title>", content, re.IGNORECASE | re.DOTALL)
            if title_match:
                title = title_match.group(1).strip()
                title = re.sub(r"\s+", " ", title)
                return html.unescape(title)
    except Exception as e:
        logger.warning(f"Failed to fetch webpage title for {url}: {e}")

    # Fallback to domain and path
    parsed = urllib.parse.urlparse(url)
    clean_tail = parsed.path.strip("/").split("/")[-1].replace("-", " ").replace("_", " ").title()
    return clean_tail if clean_tail else parsed.netloc

def save_web_link(url: str, user_notes: str = "") -> tuple[str, str]:
    """Saves web link to raw/ adhering to specifications."""
    now = datetime.now()
    ts_file = now.strftime("%Y%m%d_%H%M%S")
    ts_display = now.strftime("%Y-%m-%d %H:%M:%S")
    date_iso = now.strftime("%Y-%m-%d")
    
    title = extract_url_title(url)
    slug = slugify(title) if title else "link"
    if not slug:
        slug = "web-clip"
        
    filename = f"web_{ts_file}_{slug}.md"
    raw_dir = REPO_ROOT / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    target_path = raw_dir / filename
    
    md_content = f"""---
title: "{title}"
source_url: "{url}"
author: "Web Ingest Bot"
ingest_date: {date_iso}
tags:
  - web-clip
  - raw
---

# {title}

## Metadata Link
- **URL**: [{url}]({url})
- **Waktu Kliping**: {ts_display}
- **Judul Terdeteksi**: {title}

---

## Catatan Tambahan
{user_notes if user_notes else "_Tidak ada catatan tambahan._"}
"""
    target_path.write_text(md_content, encoding="utf-8")
    logger.info(f"Saved web clip to {target_path}")
    return filename, title

# ================= 2. Whisper & Multi-Tier Audio Transcription =================

def transcribe_with_groq_whisper(audio_bytes: bytes, filename: str) -> str:
    """Transcribes audio using Groq Whisper Cloud API (whisper-large-v3)."""
    boundary = "----WebKitFormBoundarySecondBrain" + str(int(time.time()))
    body = bytearray()
    
    # model field
    body.extend(f"--{boundary}\r\n".encode("utf-8"))
    body.extend(b'Content-Disposition: form-data; name="model"\r\n\r\n')
    body.extend(b"whisper-large-v3\r\n")
    
    # file field
    body.extend(f"--{boundary}\r\n".encode("utf-8"))
    body.extend(f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'.encode("utf-8"))
    body.extend(b"Content-Type: audio/ogg\r\n\r\n")
    body.extend(audio_bytes)
    body.extend(b"\r\n")
    body.extend(f"--{boundary}--\r\n".encode("utf-8"))
    
    req = urllib.request.Request(
        "https://api.groq.com/openai/v1/audio/transcriptions",
        data=bytes(body),
        headers={
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": f"multipart/form-data; boundary={boundary}"
        },
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        res = json.loads(resp.read().decode("utf-8"))
        return res.get("text", "")

def transcribe_with_openai_whisper(audio_bytes: bytes, filename: str) -> str:
    """Transcribes audio using OpenAI Whisper API (whisper-1)."""
    boundary = "----WebKitFormBoundarySecondBrain" + str(int(time.time()))
    body = bytearray()
    
    body.extend(f"--{boundary}\r\n".encode("utf-8"))
    body.extend(b'Content-Disposition: form-data; name="model"\r\n\r\n')
    body.extend(b"whisper-1\r\n")
    
    body.extend(f"--{boundary}\r\n".encode("utf-8"))
    body.extend(f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'.encode("utf-8"))
    body.extend(b"Content-Type: audio/ogg\r\n\r\n")
    body.extend(audio_bytes)
    body.extend(b"\r\n")
    body.extend(f"--{boundary}--\r\n".encode("utf-8"))
    
    req = urllib.request.Request(
        "https://api.openai.com/v1/audio/transcriptions",
        data=bytes(body),
        headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": f"multipart/form-data; boundary={boundary}"
        },
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        res = json.loads(resp.read().decode("utf-8"))
        return res.get("text", "")

def transcribe_audio(audio_bytes: bytes, filename: str, mime_type: str = "audio/ogg") -> tuple[str, str]:
    """
    Multi-Tier Transcription Engine:
    1. Local faster-whisper or whisper (if installed)
    2. Groq Whisper API (whisper-large-v3)
    3. OpenAI Whisper API (whisper-1)
    4. Google Gemini Multimodal Audio Cascade
    """
    # 1. Try Local Whisper if available
    try:
        import whisper
        temp_path = REPO_ROOT / "raw" / "audio_dumps" / filename
        model = whisper.load_model("base")
        res = model.transcribe(str(temp_path))
        if res.get("text"):
            return res["text"].strip(), "Local Whisper (base)"
    except Exception:
        pass

    # 2. Try Groq Whisper API
    if GROQ_API_KEY:
        try:
            logger.info("Transcribing via Groq Whisper API (whisper-large-v3)...")
            text = transcribe_with_groq_whisper(audio_bytes, filename)
            if text:
                return text.strip(), "Groq Whisper (whisper-large-v3)"
        except Exception as e:
            logger.warning(f"Groq Whisper failed: {e}")

    # 3. Try OpenAI Whisper API
    if OPENAI_API_KEY:
        try:
            logger.info("Transcribing via OpenAI Whisper API (whisper-1)...")
            text = transcribe_with_openai_whisper(audio_bytes, filename)
            if text:
                return text.strip(), "OpenAI Whisper (whisper-1)"
        except Exception as e:
            logger.warning(f"OpenAI Whisper failed: {e}")

    # 4. Try Gemini Multimodal Audio Cascade
    if GEMINI_API_KEY:
        try:
            logger.info("Transcribing via Gemini Multimodal Audio Engine...")
            sys.path.insert(0, str(REPO_ROOT / "scripts"))
            import ai_engine
            data, used_model = ai_engine.process_audio_with_ai(audio_bytes, mime_type=mime_type)
            transcription = data.get("transcription", "")
            if transcription:
                return transcription.strip(), f"Gemini Audio Cascade ({used_model})"
        except Exception as e:
            logger.warning(f"Gemini Audio transcription failed: {e}")

    return "_Transkripsi otomatis gagal atau API key Whisper/Gemini belum disetting._", "None"

def save_voice_dump(audio_bytes: bytes, filename_ext: str = "ogg", mime_type: str = "audio/ogg") -> tuple[str, str, str]:
    """Transcribes audio and writes raw/voice_dump_YYYYMMDD_HHMMSS.md with #voice-dump tag."""
    now = datetime.now()
    ts_file = now.strftime("%Y%m%d_%H%M%S")
    ts_display = now.strftime("%Y-%m-%d %H:%M:%S")
    date_iso = now.strftime("%Y-%m-%d")
    
    # Save raw audio file
    audio_dir = REPO_ROOT / "raw" / "audio_dumps"
    audio_dir.mkdir(parents=True, exist_ok=True)
    audio_filename = f"audio_{ts_file}.{filename_ext}"
    audio_file_path = audio_dir / audio_filename
    audio_file_path.write_bytes(audio_bytes)
    
    # Transcribe
    transcription, engine_name = transcribe_audio(audio_bytes, audio_filename, mime_type=mime_type)
    
    md_filename = f"voice_dump_{ts_file}.md"
    raw_md_path = REPO_ROOT / "raw" / md_filename
    
    md_content = f"""---
title: "Voice Dump {ts_display}"
source_title: "Telegram Voice Dump"
author: "Telegram Ingest Bot"
ingest_date: {date_iso}
tags:
  - voice-dump
  - raw
---

# Voice Dump - {ts_display}

#voice-dump

## Transkripsi
{transcription}

---

## Metadata Provenance
- **Waktu Input**: {ts_display}
- **File Audio Asli**: `[[raw/audio_dumps/{audio_filename}]]`
- **Engine Transkripsi**: `{engine_name}`
"""
    raw_md_path.write_text(md_content, encoding="utf-8")
    logger.info(f"Saved voice dump to {raw_md_path}")
    return md_filename, transcription, engine_name

# ================= 3. Quick Thought / Short Text Captures =================

def append_quick_capture(text: str) -> str:
    """Appends short text to journal/quick_captures.md with timestamp."""
    qc_file = REPO_ROOT / "journal" / "quick_captures.md"
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    if not qc_file.exists():
        qc_file.parent.mkdir(parents=True, exist_ok=True)
        initial_content = """# Quick Captures & Fleeting Thoughts

Koleksi tangkapan ide cepat, pengingat, dan pemikiran sekilas dari Telegram Ingest Gateway.

---
"""
        qc_file.write_text(initial_content, encoding="utf-8")
        
    entry = f"\n### {now_str}\n{text.strip()}\n\n---\n"
    with open(qc_file, "a", encoding="utf-8") as f:
        f.write(entry)
        
    logger.info(f"Appended quick thought to {qc_file}")
    return now_str

# ================= 4. Core Message Routing Logic =================

def process_incoming_text(text: str) -> dict:
    """
    Determines input type:
    - If contains URL -> save_web_link (raw/)
    - Otherwise -> append_quick_capture (journal/quick_captures.md)
    """
    clean_text = text.strip()
    url_match = re.search(r"https?://[^\s]+", clean_text)
    
    if url_match:
        url = url_match.group(0)
        remaining_notes = clean_text.replace(url, "").strip()
        filename, title = save_web_link(url, user_notes=remaining_notes)
        return {
            "type": "link",
            "filename": filename,
            "title": title,
            "url": url
        }
    else:
        ts = append_quick_capture(clean_text)
        return {
            "type": "thought",
            "timestamp": ts,
            "preview": clean_text[:120]
        }

# ================= 5. Interactive Commands (/search, /list, /read, /status) =================

def format_bot_search(query: str) -> str:
    query = query.strip()
    if not query:
        return "🔍 Format: `/search <kata kunci>`\nContoh: `/search scoring musiman`"
    try:
        sys.path.insert(0, str(REPO_ROOT / "tools"))
        import search
        hits = search.search_vault(query, top_k=3, verbose=False)
        if not hits:
            return f"🔍 *Pencarian:* `{query}`\n\n_Tidak ditemukan catatan yang cocok di vault._"
        reply = f"🔍 *Hasil Pencarian:* `{query}` ({len(hits)} catatan)\n\n"
        for idx, h in enumerate(hits, start=1):
            file_path = h.get("file_path", "")
            title = h.get("title", "Tanpa Judul")
            stem = Path(file_path).stem if file_path else ""
            clean_stem = re.sub(r"[^a-zA-Z0-9_]", "_", stem)
            cmd_slug = f"/read_{clean_stem}"
            content = h.get("content", "")
            snippet = content[:120].replace("\n", " ").replace("*", "").replace("`", "").strip()
            clean_title = title.replace("*", "").replace("`", "")
            reply += f"*{idx}. {clean_title}*\n"
            reply += f"📁 `{file_path}`\n"
            reply += f"_{snippet}..._\n"
            reply += f"📖 Baca: {cmd_slug}\n\n"
        reply += "💡 _Klik perintah di atas untuk membaca dokumen langsung di Telegram._"
        return reply
    except Exception as e:
        return f"❌ *Error saat mencari:* `{e}`"

def format_bot_list() -> str:
    try:
        dirs = ["wiki", "in_motion", "lattices", "journal"]
        notes = []
        for d in dirs:
            p = REPO_ROOT / d
            if not p.exists():
                continue
            for f in p.glob("**/*.md"):
                if f.name in ("index.md", "README.md", "INDEX.md"):
                    continue
                title = f.stem.replace("-", " ").title()
                try:
                    m = re.search(r"^title:\s*[\"']?(.*?)[\"']?$", f.read_text(encoding="utf-8")[:500], re.MULTILINE)
                    if m:
                        title = m.group(1).strip()
                except Exception:
                    pass
                notes.append((f.stat().st_mtime, title, f.stem, f.relative_to(REPO_ROOT).as_posix()))
        notes.sort(key=lambda x: x[0], reverse=True)
        if not notes:
            return "📚 Vault Anda belum memiliki catatan."
        reply = f"📚 *Catatan Terbaru di Second Brain ({len(notes)} total):*\n\n"
        for idx, (_, title, stem, rel) in enumerate(notes[:10], start=1):
            clean_stem = re.sub(r"[^a-zA-Z0-9_]", "_", stem)
            cmd = f"/read_{clean_stem}"
            clean_title = title.replace("*", "").replace("`", "")
            reply += f"*{idx}. {clean_title}*\n"
            reply += f"📁 `{rel}`\n"
            reply += f"👉 {cmd}\n\n"
        reply += "💡 _Klik perintah di atas untuk membaca isi catatan langsung di Telegram._"
        return reply
    except Exception as e:
        return f"❌ *Gagal memuat daftar catatan:* `{e}`"

def format_bot_read(target_slug: str) -> list[str]:
    target = target_slug.strip("/_ ").replace("-", " ").replace("_", " ").lower()
    if not target:
        return ["ℹ️ Format: `/read <nama-catatan>` atau ketik `/list` untuk memilih."]
    
    matched_file = None
    matched_title = target
    for f in REPO_ROOT.glob("**/*.md"):
        if any(skip in f.parts for skip in [".git", "node_modules", ".obsidian"]):
            continue
        stem_norm = f.stem.replace("-", " ").replace("_", " ").lower()
        if target == stem_norm or target in stem_norm:
            matched_file = f
            try:
                m = re.search(r"^title:\s*[\"']?(.*?)[\"']?$", f.read_text(encoding="utf-8")[:500], re.MULTILINE)
                if m:
                    matched_title = m.group(1).strip()
            except Exception:
                pass
            break
            
    if not matched_file:
        return [f"❌ Catatan `{target_slug}` tidak ditemukan.\nKetik `/list` untuk daftar catatan atau `/search {target_slug}`."]
        
    try:
        content = matched_file.read_text(encoding="utf-8")
        rel_path = matched_file.relative_to(REPO_ROOT).as_posix()
        header = f"📄 *{matched_title}*\n📁 `{rel_path}`\n───────────────\n\n"
        full = header + content
        chunks = []
        chunk_size = 3800
        for i in range(0, len(full), chunk_size):
            chunks.append(full[i:i+chunk_size])
        return chunks
    except Exception as e:
        return [f"❌ Gagal membaca file: {e}"]

def format_bot_status() -> str:
    try:
        db_path = REPO_ROOT / "data" / "vault_search.db"
        db_size = f"{db_path.stat().st_size / 1024:.1f} KB" if db_path.exists() else "Belum terindeks"
        notes_count = sum(1 for f in REPO_ROOT.glob("**/*.md") if not any(k in f.parts for k in [".git", ".obsidian"]))
        raw_pending = sum(1 for f in (REPO_ROOT / "raw").glob("*.md")) if (REPO_ROOT / "raw").exists() else 0
        model_name = globals().get("GEMINI_MODEL", os.getenv("GEMINI_MODEL", "gemini-3.8-flash"))
        whisper_engine = "Groq (whisper-large-v3)" if GROQ_API_KEY else "Gemini Multimodal"
        return (
            f"📊 *Second Brain System Status*\n\n"
            f"📚 *Total Catatan:* `{notes_count}` file Markdown\n"
            f"📥 *Raw Inbox Pending:* `{raw_pending}` file belum di-ingest\n"
            f"🔍 *Search Index:* `{db_size}` (SQLite)\n"
            f"🤖 *Gemini Model:* `{model_name}`\n"
            f"⚡ *Whisper Engine:* `{whisper_engine}`\n\n"
            f"Perintah cepat:\n"
            f"• `/list` -> Daftar 10 catatan terbaru\n"
            f"• `/search <kueri>` -> Cari catatan\n"
            f"• `/help` -> Bantuan lengkap"
        )
    except Exception as e:
        return f"❌ *Gagal memuat status sistem:* `{e}`"

def format_bot_warroom(decision: str) -> str:
    decision = decision.strip()
    if not decision:
        return (
            "💀 *Format War Room Pre-Mortem:*\n"
            "`/warroom <rencana atau keputusan Anda>`\n\n"
            "Contoh:\n"
            "`/warroom Menerima proyek konsultasi enterprise senilai Rp 150 juta dengan klausul penalti denda keterlambatan`"
        )
    try:
        sys.path.insert(0, str(REPO_ROOT / "tools"))
        import war_room
        
        journals = war_room.scan_journal_biases()
        crms = war_room.scan_crm_contacts()
        tech = war_room.scan_technical_assumptions(decision)
        
        data = war_room.call_gemini_war_room(decision, journals, crms, tech)
        if not data:
            data = war_room.generate_heuristic_war_room(decision, journals, crms)
            
        md_content, slug = war_room.format_war_room_markdown(decision, data, journals, crms, tech)
        target_filename = f"war_room_{slug}.md"
        target_file = REPO_ROOT / "in_motion" / target_filename
        target_file.parent.mkdir(parents=True, exist_ok=True)
        target_file.write_text(md_content, encoding="utf-8")
        
        war_room.update_indexes(target_filename, f"War Room Pre-Mortem: {data.get('project_title', decision)}")
        war_room.log_operation(target_file.stem, decision)
        
        # Build executive summary
        title = data.get("project_title", decision)
        thesis = data.get("executive_premortem_thesis", "")
        
        fms = data.get("failure_modes", [])
        fm_text = ""
        for idx, fm in enumerate(fms, 1):
            fm_text += f"{idx}. *{fm['scenario']}* (`{fm.get('probability', 'Tinggi')}`)\n   ⚠️ Pemicu: _{fm['trigger_event']}_\n"
            
        questions = data.get("blindspot_questions", [])
        q_text = "\n".join([f"{idx}. {q}" for idx, q in enumerate(questions, 1)])
        
        mitigs = data.get("actionable_mitigations", [])
        mitig_text = ""
        for idx, am in enumerate(mitigs, 1):
            mitig_text += f"• *{am['action']}*\n   Batas Toleransi: `{am['metric_threshold']}`\n"
            
        reply = (
            f"💀 *WAR ROOM PRE-MORTEM EXECUTIVE SUMMARY*\n"
            f"🎯 *Target:* `{title}`\n\n"
            f"⚡ *Retrospektif Kegagalan dari Masa Depan:*\n"
            f"_{thesis}_\n\n"
            f"🔥 *3 Skenario Kegagalan Paling Realistis:*\n"
            f"{fm_text}\n"
            f"❓ *5 Pertanyaan Blindspot Wajib:*\n"
            f"{q_text}\n\n"
            f"🛡️ *Actionable Mitigation & Kill-Switch:*\n"
            f"{mitig_text}\n"
            f"📁 *Dokumen lengkap tersimpan di:* `in_motion/{target_filename}`\n"
            f"📖 Baca full: `/read {target_file.stem}`"
        )
        return reply
    except Exception as e:
        return f"❌ *Gagal menjalankan War Room:* `{e}`"

def format_bot_weave(args_text: str) -> str:
    parts = re.split(r"\s+(?:dan|x|\&)\s+", args_text.strip(), flags=re.IGNORECASE)
    if len(parts) < 2:
        return (
            "🕸️ *Format Operasi WEAVE:*\n"
            "`/weave <Domain A> x <Domain B>`\n\n"
            "Contoh:\n"
            "`/weave Credit Risk x Tactical Football Analytics`"
        )
    domain_a = parts[0].strip()
    domain_b = parts[1].strip()
    try:
        sys.path.insert(0, str(REPO_ROOT / "tools"))
        import weave
        
        ctx_a = weave.search_vault_for_domain(domain_a, top_k=2)
        ctx_b = weave.search_vault_for_domain(domain_b, top_k=2)
        backlinks = [f"[[{Path(d['path']).stem}]]" for d in ctx_a + ctx_b]
        
        data = weave.call_gemini_synthesis(domain_a, domain_b, ctx_a, ctx_b)
        if not data:
            data = weave.generate_heuristic_synthesis(domain_a, domain_b)
            
        slug_a = weave.slugify(domain_a.split("/")[0])
        slug_b = weave.slugify(domain_b.split("/")[0])
        target_filename = f"synthesis_{slug_a}_{slug_b}.md"
        target_file = REPO_ROOT / "wiki" / target_filename
        
        md_content = weave.format_synthesis_markdown(domain_a, domain_b, data, backlinks)
        target_file.parent.mkdir(parents=True, exist_ok=True)
        target_file.write_text(md_content, encoding="utf-8")
        
        weave.update_indexes(target_filename, f"Sintesis Lintas Domain: {domain_a} x {domain_b}", domain_a, domain_b)
        weave.log_operation(target_file.stem, domain_a, domain_b)
        
        transfers_text = ""
        for idx, t in enumerate(data.get("transfers", []), 1):
            transfers_text += f"{idx}. *{t['title']}*\n   💡 {t['concrete_solution'][:150]}...\n\n"
            
        reply = (
            f"🕸️ *SINTESIS LINTAS DOMAIN (WEAVE)*\n"
            f"🔬 *{domain_a}* ✖️ *{domain_b}*\n\n"
            f"📌 *Tesis Isomorfik:*\n_{data.get('thesis', '')[:350]}..._\n\n"
            f"🚀 *Transfer Ilmu Konkret:*\n{transfers_text}"
            f"📁 *Dokumen lengkap:* `wiki/{target_filename}`\n"
            f"📖 Baca full: `/read {target_file.stem}`"
        )
        return reply
    except Exception as e:
        return f"❌ *Gagal menjalankan WEAVE:* `{e}`"

def format_bot_ingest() -> str:
    raw_dir = REPO_ROOT / "raw"
    if not raw_dir.exists():
        return "📥 Folder `raw/` belum ada. Belum ada catatan mentah."
        
    items = [f for f in raw_dir.iterdir() if f.is_file() and not f.name.startswith(".")]
    if not items:
        return "📥 *Semua file mentah sudah terproses!*\nFolder `raw/` bersih. Belum ada voice note atau web clip baru yang pending."
        
    try:
        sys.path.insert(0, str(REPO_ROOT / "scripts"))
        import ingest
        processed_files = []
        for f in items:
            success = ingest.ingest_raw_to_wiki(f)
            if success:
                processed_files.append(f.name)
                
        # Re-index
        try:
            sys.path.insert(0, str(REPO_ROOT / "tools"))
            import indexer
            indexer.build_index(verbose=False)
        except Exception:
            pass
            
        file_list = "\n".join([f"• `{fn}`" for fn in processed_files])
        reply = (
            f"⚡ *AUTONOMOUS INGESTION COMPLETED!*\n\n"
            f"📥 *Berhasil memproses {len(processed_files)} file mentah:*\n"
            f"{file_list}\n\n"
            f"✨ Seluruh intisari telah diekstrak ke `wiki/`, profil dipetakan ke `crm/`, dan file asli diarsipkan ke `raw/processed/`.\n"
            f"Ketik `/list` untuk membaca catatan baru."
        )
        return reply
    except Exception as e:
        return f"❌ *Gagal memproses ingest:* `{e}`"

def format_bot_weekly() -> str:
    try:
        sys.path.insert(0, str(REPO_ROOT / "tools"))
        import weekly_synthesis
        
        target_file, audit = weekly_synthesis.run_weekly_synthesis(dry_run=False)
        
        now = datetime.now()
        year, week_num, _ = now.isocalendar()
        week_id = f"{year}-W{week_num:02d}"
        
        wins = audit.get("wins", [])
        wins_text = "\n".join([f"• {w}" for w in wins[:3]]) if wins else "• Eksekusi sistem berjalan lancar."
        
        obstacles = audit.get("recurring_obstacles", [])
        obs_text = "\n".join([f"⚠️ {o}" for o in obstacles[:3]]) if obstacles else "• Tidak ada hambatan berulang yang terdeteksi."
        
        conflicts = audit.get("cognitive_conflicts", [])
        conf_text = "\n".join([f"⚡ {c}" for c in conflicts[:2]]) if conflicts else "• Tidak ada kontradiksi prinsip signifikan."
        
        tactics = audit.get("tactical_recommendations", [])
        tact_text = "\n".join([f"{idx}. *{t}*" for idx, t in enumerate(tactics[:3], 1)]) if tactics else "1. Pertahankan konsistensi jurnal.\n2. Review deliverable aktif."
        
        reply = (
            f"🧠 *AUDIT KOGNITIF MINGGUAN ({week_id})*\n"
            f"📅 _Evaluasi Jurnal & Sistem 7 Hari Terakhir_\n\n"
            f"🏆 *Wins & Strategic Progress:*\n{wins_text}\n\n"
            f"🚧 *Hambatan Berulang (Recurring Obstacles):*\n{obs_text}\n\n"
            f"⚔️ *Friksi & Kontradiksi Kognitif:*\n{conf_text}\n\n"
            f"🎯 *3 Rekomendasi Taktis Minggu Depan:*\n{tact_text}\n\n"
            f"📁 *Dokumen lengkap:* `journal/weekly_briefings/{week_id}.md`\n"
            f"📖 Baca full: `/read {week_id}`"
        )
        return reply
    except Exception as e:
        logger.error(f"Error in format_bot_weekly: {e}")
        return f"❌ *Gagal menjalankan Audit Mingguan:* `{e}`"

def format_bot_sync() -> str:
    try:
        sys.path.insert(0, str(REPO_ROOT / "tools"))
        idx_msg = "✅ Search index (BM25 + Semantic) up-to-date."
        try:
            import indexer
            indexer.build_index(verbose=False)
        except Exception as e:
            idx_msg = f"⚠️ Indexer: {e}"

        import subprocess
        git_steps = []
        subprocess.run(["git", "add", "."], cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=20)
        diff = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=str(REPO_ROOT))
        if diff.returncode != 0:
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
            subprocess.run(["git", "commit", "-m", f"chore(sync): automated sync via telegram {now_str}"], cwd=str(REPO_ROOT), capture_output=True, text=True)
            git_steps.append(f"📦 Local commit dibuat: `{now_str}`")
        else:
            git_steps.append("📦 Vault lokal sudah bersih (up-to-date).")

        push = subprocess.run(["git", "push", "origin", "main"], cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=25)
        if push.returncode == 0:
            git_steps.append("🚀 Pushed ke GitHub origin/main.")
        else:
            err_line = (push.stderr or push.stdout or "Push terminal bypass active").strip()[:80]
            git_steps.append(f"ℹ️ Git Push: `{err_line}`")

        sync_summary = "\n".join(git_steps)
        reply = (
            f"🔄 *VAULT MULTI-DEVICE SYNCHRONIZATION*\n\n"
            f"{idx_msg}\n\n"
            f"{sync_summary}\n\n"
            f"💡 *Obsidian PC*: Jalankan `sync_vault.ps1` atau `git pull` di PC untuk menerima pembaruan ini."
        )
        return reply
    except Exception as e:
        return f"❌ *Gagal melakukan sinkronisasi:* `{e}`"

def format_bot_help() -> str:
    return (
        "🧠 *Panduan Second Brain Telegram Ingest Bot*\n\n"
        "📥 *Cara Menangkap Input dari HP:*\n"
        "• *Voice Note / VN*: Cukup rekam suara langsung. Bot otomatis mentranskripsi via Whisper dan menyimpannya ke `raw/`.\n"
        "• *Link Web / YouTube*: Kirim URL link. Judul dan konten akan diekstrak otomatis ke `raw/`.\n"
        "• *Pikiran / Catatan Singkat*: Kirim teks pendek. Otomatis masuk ke `journal/quick_captures.md` dengan timestamp.\n\n"
        "⚡ *Autonomous Pipeline & Triage:*\n"
        "• `/ingest` - Proses seluruh file mentah di `raw/` ke `wiki/` dan profil `crm/`\n\n"
        "⚔️ *Operasi Strategis & Kognitif:*\n"
        "• `/warroom <keputusan>` - Jalankan War Room Pre-Mortem Red Team untuk menguji risiko rencana Anda\n"
        "• `/weave <Domain A> x <Domain B>` - Sintesis analogi struktural lintas domain\n"
        "• `/weekly` - Jalankan Audit Kognitif Mingguan (evaluasi hambatan & 3 rekomendasi taktis)\n\n"
        "🔄 *Sinkronisasi & Pemeliharaan:*\n"
        "• `/sync` - Sinkronkan vault dengan remote Git dan perbarui search index\n"
        "• `/status` - Cek kesehatan sistem & database\n\n"
        "🔎 *Perintah Interaktif:*\n"
        "• `/search <kueri>` - Cari catatan via Hybrid Search (BM25 + Vektor)\n"
        "• `/list` - Tampilkan daftar catatan terbaru dengan tombol baca\n"
        "• `/read <nama_file>` - Baca catatan langsung di Telegram\n"
        "• `/help` - Tampilkan bantuan ini"
    )

# ================= 6. Implementation Engines =================

# --- A. python-telegram-bot (v20+ Async Implementation) ---
try:
    from telegram import Update
    from telegram.ext import (
        ApplicationBuilder,
        CommandHandler,
        MessageHandler,
        ContextTypes,
        filters
    )
    HAS_PTB = True
except ImportError:
    HAS_PTB = False

async def ptb_safe_reply(msg_target, text: str, parse_mode: str = "Markdown"):
    """Resilient message sender: attempts parse_mode, falls back to plain text if formatting errors occur."""
    try:
        return await msg_target.reply_text(text, parse_mode=parse_mode)
    except Exception as e:
        logger.warning(f"Markdown reply failed ({e}), retrying plain text")
        try:
            return await msg_target.reply_text(text)
        except Exception as e2:
            logger.error(f"Plain text reply also failed: {e2}")

async def ptb_safe_edit(msg, text: str, parse_mode: str = "Markdown"):
    """Resilient message editor: attempts parse_mode, falls back to plain text if formatting errors occur."""
    try:
        return await msg.edit_text(text, parse_mode=parse_mode)
    except Exception as e:
        logger.warning(f"Markdown edit failed ({e}), retrying plain text")
        try:
            return await msg.edit_text(text)
        except Exception as e2:
            logger.error(f"Plain text edit also failed: {e2}")

async def ptb_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if ALLOWED_USER_ID and user_id != str(ALLOWED_USER_ID):
        await ptb_safe_reply(update.message, f"⛔ Akses Ditolak. User ID `{user_id}` tidak terdaftar.")
        return
    await ptb_safe_reply(update.message, format_bot_help())

async def ptb_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await ptb_start(update, context)

async def ptb_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if ALLOWED_USER_ID and user_id != str(ALLOWED_USER_ID):
        return
    await ptb_safe_reply(update.message, format_bot_status())

async def ptb_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if ALLOWED_USER_ID and user_id != str(ALLOWED_USER_ID):
        return
    await ptb_safe_reply(update.message, format_bot_list())

async def ptb_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if ALLOWED_USER_ID and user_id != str(ALLOWED_USER_ID):
        return
    query = " ".join(context.args).strip() if context.args else ""
    await ptb_safe_reply(update.message, format_bot_search(query))

async def ptb_read(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if ALLOWED_USER_ID and user_id != str(ALLOWED_USER_ID):
        return
    target = " ".join(context.args).strip() if context.args else ""
    chunks = format_bot_read(target)
    for c in chunks:
        await ptb_safe_reply(update.message, c)

async def ptb_warroom(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if ALLOWED_USER_ID and user_id != str(ALLOWED_USER_ID):
        return
    decision = " ".join(context.args).strip() if context.args else ""
    status_msg = await update.message.reply_text("💀 *Menjalankan simulasi War Room Pre-Mortem Red Team...*", parse_mode="Markdown")
    reply = format_bot_warroom(decision)
    await ptb_safe_edit(status_msg, reply)

async def ptb_weave(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if ALLOWED_USER_ID and user_id != str(ALLOWED_USER_ID):
        return
    args = " ".join(context.args).strip() if context.args else ""
    status_msg = await update.message.reply_text("🕸️ *Menjalankan sintesis lintas domain WEAVE...*", parse_mode="Markdown")
    reply = format_bot_weave(args)
    await ptb_safe_edit(status_msg, reply)

async def ptb_ingest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if ALLOWED_USER_ID and user_id != str(ALLOWED_USER_ID):
        return
    msg = await update.message.reply_text("⚡ *Menjalankan Autonomous Ingest Pipeline...*", parse_mode="Markdown")
    reply = format_bot_ingest()
    await ptb_safe_edit(msg, reply)

async def ptb_weekly(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if ALLOWED_USER_ID and user_id != str(ALLOWED_USER_ID):
        return
    msg = await update.message.reply_text("🧠 *Menjalankan Audit Kognitif Mingguan...*", parse_mode="Markdown")
    reply = format_bot_weekly()
    await ptb_safe_edit(msg, reply)

async def ptb_sync(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if ALLOWED_USER_ID and user_id != str(ALLOWED_USER_ID):
        return
    msg = await update.message.reply_text("🔄 *Menjalankan sinkronisasi multi-perangkat...*", parse_mode="Markdown")
    reply = format_bot_sync()
    await ptb_safe_edit(msg, reply)

async def ptb_handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if ALLOWED_USER_ID and user_id != str(ALLOWED_USER_ID):
        logger.warning(f"Unauthorized text attempt from user {user_id}")
        await ptb_safe_reply(update.message, f"⛔ Akses Ditolak. User ID `{user_id}` tidak terdaftar.")
        return

    text = update.message.text.strip()
    lower_text = text.lower()
    
    # Intercept Ingest trigger
    if text in ("/ingest", "/ingest all", "/proses"):
        msg = await update.message.reply_text("⚡ *Menjalankan Autonomous Ingest Pipeline...*", parse_mode="Markdown")
        reply = format_bot_ingest()
        await ptb_safe_edit(msg, reply)
        return

    # Intercept War Room / Pre-Mortem commands or prefix triggers
    if text.startswith(("/warroom", "/premortem")):
        decision = re.sub(r"^/(?:warroom|premortem)\s*", "", text).strip()
        status_msg = await update.message.reply_text("💀 *Menjalankan simulasi War Room Pre-Mortem Red Team...*", parse_mode="Markdown")
        reply = format_bot_warroom(decision)
        await ptb_safe_edit(status_msg, reply)
        return
    elif lower_text.startswith(("war room:", "warroom:", "pre-mortem:", "premortem:", "uji keputusan:")):
        decision = re.sub(r"^(?:war\s*room|warroom|pre-?mortem|uji\s*keputusan):\s*", "", text, flags=re.IGNORECASE).strip()
        status_msg = await update.message.reply_text("💀 *Menjalankan simulasi War Room Pre-Mortem Red Team...*", parse_mode="Markdown")
        reply = format_bot_warroom(decision)
        await ptb_safe_edit(status_msg, reply)
        return
    elif text.startswith("/weave"):
        args = text[6:].strip()
        status_msg = await update.message.reply_text("🕸️ *Menjalankan sintesis lintas domain WEAVE...*", parse_mode="Markdown")
        reply = format_bot_weave(args)
        await ptb_safe_edit(status_msg, reply)
        return

    # Intercept direct /read_ commands
    if text.startswith("/read_"):
        slug = text[6:].replace("_", "-")
        chunks = format_bot_read(slug)
        for c in chunks:
            await ptb_safe_reply(update.message, c)
        return
    elif text.startswith("/read"):
        slug = text[5:].strip().replace("_", "-")
        chunks = format_bot_read(slug)
        for c in chunks:
            await ptb_safe_reply(update.message, c)
        return
    elif text.startswith("/search"):
        q = text[7:].strip()
        await ptb_safe_reply(update.message, format_bot_search(q))
        return
    elif text == "/list":
        await ptb_safe_reply(update.message, format_bot_list())
        return
    elif text == "/status":
        await ptb_safe_reply(update.message, format_bot_status())
        return
    elif text in ("/weekly", "/audit"):
        msg = await update.message.reply_text("🧠 *Menjalankan Audit Kognitif Mingguan...*", parse_mode="Markdown")
        reply = format_bot_weekly()
        await ptb_safe_edit(msg, reply)
        return
    elif text == "/sync":
        msg = await update.message.reply_text("🔄 *Menjalankan sinkronisasi multi-perangkat...*", parse_mode="Markdown")
        reply = format_bot_sync()
        await ptb_safe_edit(msg, reply)
        return

    res = process_incoming_text(text)
    
    if res["type"] == "link":
        reply = (
            f"🔗 *Link Web Berhasil Disimpan!*\n\n"
            f"📌 *Judul:* {res['title']}\n"
            f"📁 *File Raw:* `raw/{res['filename']}`\n"
            f"🌐 *URL:* {res['url']}"
        )
    else:
        reply = (
            f"📝 *Quick Thought Dicatat!*\n\n"
            f"🕒 *Timestamp:* `{res['timestamp']}`\n"
            f"📖 *Lokasi:* `journal/quick_captures.md`\n"
            f"💬 _{res['preview']}..._"
        )
    await update.message.reply_text(reply, parse_mode="Markdown")

async def ptb_handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if ALLOWED_USER_ID and user_id != str(ALLOWED_USER_ID):
        logger.warning(f"Unauthorized voice attempt from user {user_id}")
        await update.message.reply_text(f"⛔ Akses Ditolak. User ID `{user_id}` tidak terdaftar.", parse_mode="Markdown")
        return

    msg = await update.message.reply_text("🎙️ *Mengunduh dan mentranskripsi voice note...*", parse_mode="Markdown")
    
    voice = update.message.voice or update.message.audio
    file_obj = await context.bot.get_file(voice.file_id)
    audio_bytes = await file_obj.download_as_bytearray()
    
    mime = "audio/ogg" if update.message.voice else (voice.mime_type or "audio/mp3")
    ext = "ogg" if update.message.voice else "mp3"
    
    md_file, transcript, engine = save_voice_dump(bytes(audio_bytes), filename_ext=ext, mime_type=mime)
    
    snippet = transcript[:200] + ("..." if len(transcript) > 200 else "")
    reply = (
        f"✅ *Voice Note Berhasil Dikonversi!*\n\n"
        f"🤖 *Engine:* `{engine}`\n"
        f"📁 *File:* `raw/{md_file}`\n"
        f"🏷️ *Tag:* `#voice-dump`\n\n"
        f"🗣️ *Transkrip:*\n_{snippet}_"
    )
    await msg.edit_text(reply, parse_mode="Markdown")

def run_ptb():
    """Runs bot using python-telegram-bot library."""
    logger.info("Initializing bot with python-telegram-bot engine...")
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", ptb_start))
    app.add_handler(CommandHandler("help", ptb_help))
    app.add_handler(CommandHandler("status", ptb_status))
    app.add_handler(CommandHandler("list", ptb_list))
    app.add_handler(CommandHandler("search", ptb_search))
    app.add_handler(CommandHandler("read", ptb_read))
    app.add_handler(CommandHandler("warroom", ptb_warroom))
    app.add_handler(CommandHandler("premortem", ptb_warroom))
    app.add_handler(CommandHandler("weave", ptb_weave))
    app.add_handler(CommandHandler("ingest", ptb_ingest))
    app.add_handler(CommandHandler("weekly", ptb_weekly))
    app.add_handler(CommandHandler("audit", ptb_weekly))
    app.add_handler(CommandHandler("sync", ptb_sync))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), ptb_handle_text))
    app.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, ptb_handle_voice))
    
    logger.info("Starting python-telegram-bot polling...")
    app.run_polling()

# --- B. Resilient Built-in Polling Fallback (Zero-Dependency) ---
def run_builtin_fallback():
    """Built-in polling engine if python-telegram-bot is not installed yet."""
    logger.info("python-telegram-bot not detected. Running built-in zero-dependency polling loop...")
    
    def tg_call(method: str, payload: dict) -> dict:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/{method}"
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=35) as resp:
            return json.loads(resp.read().decode("utf-8"))
            
    def send_tg_msg(chat_id: int, text: str):
        try:
            tg_call("sendMessage", {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"})
        except Exception as e:
            logger.warning(f"Markdown send failed ({e}), falling back to plain text")
            try:
                tg_call("sendMessage", {"chat_id": chat_id, "text": text})
            except Exception as e2:
                logger.error(f"Failed to send plain text message: {e2}")

    last_offset = 0
    while True:
        try:
            updates = tg_call("getUpdates", {"offset": last_offset + 1, "timeout": 30})
            for item in updates.get("result", []):
                last_offset = item["update_id"]
                msg = item.get("message")
                if not msg:
                    continue
                    
                sender_id = str(msg.get("from", {}).get("id", ""))
                chat_id = msg.get("chat", {}).get("id")
                
                # Security whitelist check
                if ALLOWED_USER_ID and sender_id != str(ALLOWED_USER_ID):
                    logger.warning(f"Unauthorized access attempt from user_id: {sender_id}")
                    send_tg_msg(chat_id, f"⛔ *Akses Ditolak.* User ID `{sender_id}` tidak terdaftar.")
                    continue
                    
                # 1. Text Message
                if "text" in msg:
                    text = msg["text"].strip()
                    lower_text = text.lower()
                    if text in ("/start", "/help"):
                        send_tg_msg(chat_id, format_bot_help())
                        continue
                    elif text in ("/ingest", "/ingest all", "/proses"):
                        send_tg_msg(chat_id, "⚡ *Menjalankan Autonomous Ingest Pipeline...*")
                        send_tg_msg(chat_id, format_bot_ingest())
                        continue
                    elif text.startswith(("/warroom", "/premortem")):
                        decision = re.sub(r"^/(?:warroom|premortem)\s*", "", text).strip()
                        send_tg_msg(chat_id, "💀 *Menjalankan simulasi War Room Pre-Mortem Red Team...*")
                        send_tg_msg(chat_id, format_bot_warroom(decision))
                        continue
                    elif lower_text.startswith(("war room:", "warroom:", "pre-mortem:", "premortem:", "uji keputusan:")):
                        decision = re.sub(r"^(?:war\s*room|warroom|pre-?mortem|uji\s*keputusan):\s*", "", text, flags=re.IGNORECASE).strip()
                        send_tg_msg(chat_id, "💀 *Menjalankan simulasi War Room Pre-Mortem Red Team...*")
                        send_tg_msg(chat_id, format_bot_warroom(decision))
                        continue
                    elif text.startswith("/weave"):
                        args = text[6:].strip()
                        send_tg_msg(chat_id, "🕸️ *Menjalankan sintesis lintas domain WEAVE...*")
                        send_tg_msg(chat_id, format_bot_weave(args))
                        continue
                    elif text == "/status":
                        send_tg_msg(chat_id, format_bot_status())
                        continue
                    elif text == "/list":
                        send_tg_msg(chat_id, format_bot_list())
                        continue
                    elif text.startswith("/search"):
                        q = text[7:].strip()
                        send_tg_msg(chat_id, format_bot_search(q))
                        continue
                    elif text.startswith("/read_"):
                        slug = text[6:].replace("_", "-")
                        chunks = format_bot_read(slug)
                        for c in chunks:
                            send_tg_msg(chat_id, c)
                        continue
                    elif text.startswith("/read"):
                        slug = text[5:].strip().replace("_", "-")
                        chunks = format_bot_read(slug)
                        for c in chunks:
                            send_tg_msg(chat_id, c)
                        continue
                    elif text in ("/weekly", "/audit"):
                        send_tg_msg(chat_id, "🧠 *Menjalankan Audit Kognitif Mingguan...*")
                        send_tg_msg(chat_id, format_bot_weekly())
                        continue
                    elif text == "/sync":
                        send_tg_msg(chat_id, "🔄 *Menjalankan sinkronisasi multi-perangkat...*")
                        send_tg_msg(chat_id, format_bot_sync())
                        continue
                        
                    res = process_incoming_text(text)
                    if res["type"] == "link":
                        reply = (
                            f"🔗 *Link Web Berhasil Disimpan!*\n\n"
                            f"📌 *Judul:* {res['title']}\n"
                            f"📁 *File Raw:* `raw/{res['filename']}`\n"
                            f"🌐 *URL:* {res['url']}"
                        )
                    else:
                        reply = (
                            f"📝 *Quick Thought Dicatat!*\n\n"
                            f"🕒 *Timestamp:* `{res['timestamp']}`\n"
                            f"📖 *Lokasi:* `journal/quick_captures.md`\n"
                            f"💬 _{res['preview']}..._"
                        )
                    send_tg_msg(chat_id, reply)
                    
                # 2. Voice Note / Audio
                elif "voice" in msg or "audio" in msg:
                    send_tg_msg(chat_id, "🎙️ *Mengunduh dan mentranskripsi voice note...*")
                    voice = msg.get("voice") or msg.get("audio")
                    f_id = voice["file_id"]
                    
                    # Get file path from Telegram API
                    f_info = tg_call("getFile", {"file_id": f_id})
                    file_path = f_info.get("result", {}).get("file_path")
                    if file_path:
                        dl_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
                        req = urllib.request.Request(dl_url)
                        with urllib.request.urlopen(req, timeout=60) as resp:
                            audio_bytes = resp.read()
                            
                        ext = "ogg" if "voice" in msg else "mp3"
                        mime = "audio/ogg" if "voice" in msg else voice.get("mime_type", "audio/mp3")
                        md_file, transcript, engine = save_voice_dump(audio_bytes, filename_ext=ext, mime_type=mime)
                        
                        snippet = transcript[:200] + ("..." if len(transcript) > 200 else "")
                        reply = (
                            f"✅ *Voice Note Berhasil Dikonversi!*\n\n"
                            f"🤖 *Engine:* `{engine}`\n"
                            f"📁 *File:* `raw/{md_file}`\n"
                            f"🏷️ *Tag:* `#voice-dump`\n\n"
                            f"🗣️ *Transkrip:*\n_{snippet}_"
                        )
                        send_tg_msg(chat_id, reply)
                    else:
                        send_tg_msg(chat_id, "❌ *Gagal mengunduh file audio dari Telegram.*")
                        
        except KeyboardInterrupt:
            logger.info("Bot stopped by user.")
            break
        except Exception as e:
            logger.error(f"Polling loop error: {e}")
            time.sleep(5)

def main():
    if not BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN is not set in .env! Exiting...")
        print("[!] ERROR: TELEGRAM_BOT_TOKEN is not configured in .env.")
        print("[*] Dapatkan token dari @BotFather dan masukkan ke .env.")
        sys.exit(1)
        
    if ALLOWED_USER_ID:
        logger.info(f"Security active: restricted strictly to Telegram User ID: {ALLOWED_USER_ID}")
    else:
        logger.warning("No TELEGRAM_ALLOWED_USER_ID configured. The bot is open to all users.")

    if HAS_PTB:
        run_ptb()
    else:
        run_builtin_fallback()

if __name__ == "__main__":
    main()
