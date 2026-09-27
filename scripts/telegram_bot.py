#!/usr/bin/env python3
"""
Telegram Ingest Bot: Second Brain Voice & Text Capture Gateway
Pure Python 3 Standard Library (Zero external pip dependencies).
Supports:
1. Text dumps & quick thoughts
2. Voice notes & audio files (transcribed & ingested natively via Gemini 3.8 Flash multimodal API)
3. Instant routing to inbox_raw/ -> ingest.py -> graph_index.py
4. Telegram Commands: /search <query>, /status, /pulse
"""

import os
import sys
import json
import time
import base64
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import ingest
import graph_index

def load_env():
    """Loads environment variables from .env file."""
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

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ALLOWED_USER_ID = os.getenv("TELEGRAM_ALLOWED_USER_ID")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")

TELEGRAM_API_BASE = f"https://api.telegram.org/bot{BOT_TOKEN}"
TELEGRAM_FILE_BASE = f"https://api.telegram.org/file/bot{BOT_TOKEN}"

def tg_request(method: str, data: dict = None) -> dict:
    """Executes a Telegram Bot API request using urllib."""
    url = f"{TELEGRAM_API_BASE}/{method}"
    headers = {"Content-Type": "application/json"}
    body = json.dumps(data).encode("utf-8") if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method="POST" if body else "GET")
    
    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"[-] Telegram API Error ({method}): {e}")
        return {}

def send_message(chat_id: int, text: str, parse_mode: str = "Markdown"):
    """Sends a message back to the user on Telegram with plain text fallback."""
    res = tg_request("sendMessage", {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode,
        "disable_web_page_preview": True
    })
    # If Markdown parsing fails due to unescaped special characters, fallback to plain text
    if not res.get("ok") and parse_mode:
        tg_request("sendMessage", {
            "chat_id": chat_id,
            "text": text,
            "disable_web_page_preview": True
        })

def download_file(file_id: str) -> tuple[bytes, str]:
    """Downloads a file from Telegram servers."""
    res = tg_request("getFile", {"file_id": file_id})
    if not res.get("ok"):
        return b"", ""
    
    file_path = res["result"].get("file_path", "")
    download_url = f"{TELEGRAM_FILE_BASE}/{file_path}"
    
    try:
        with urllib.request.urlopen(download_url, timeout=60) as resp:
            return resp.read(), file_path
    except Exception as e:
        print(f"[-] Error downloading file {file_id}: {e}")
        return b"", ""

def transcribe_and_ingest_audio(audio_bytes: bytes, mime_type: str = "audio/ogg") -> dict:
    """Sends audio directly to Gemini 3.8 Flash for transcription and cognitive ingest."""
    b64_audio = base64.b64encode(audio_bytes).decode("utf-8")
    
    prompt = """
You are the AI Cognitive Ingestion Engine for an AI Systems Engineer & Knowledge Architecture Specialist.
The user sent a VOICE NOTE / AUDIO DUMP.
Perform the following:
1. Accurately transcribe the spoken thoughts (default language Indonesian/English).
2. Analyze the transcript according to the user's cognitive profile:
   - deliverable-first (concrete outputs, not vague ideas)
   - high concurrency (core_work vs side_builder vs meta_system)
   - statistically grounded, executive-ready, structured tables/checklists
   - ideas pushed to deployment.

Produce a JSON response with these exact keys:
1. "transcription": The full verbatim transcription of the voice note.
2. "title": Crisp executive title.
3. "slug": kebab-case identifier.
4. "stream": One of ["core_work", "side_builder", "meta_system"].
5. "target_folder": One of ["in_motion/core_work", "in_motion/side_builder", "lattices/mental_models", "lattices/playbooks"].
6. "type": One of ["in_motion", "lattice"].
7. "status": One of ["active", "incubating", "evergreen"].
8. "tags": Array of strings.
9. "core_insights": Array of 2-4 grounded bullet points.
10. "key_entities": Array of wikilinks (e.g. ["[[eval-harness-v1]]"]).
11. "action_items": Array of checklist items starting with "- [ ]".
12. "formatted_markdown": Complete GitHub Flavored Markdown document including YAML frontmatter, audio transcription transcript block, executive summary, tables, and action items.
"""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_KEY}"
    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "inlineData": {
                            "mimeType": mime_type,
                            "data": b64_audio
                        }
                    },
                    {
                        "text": prompt
                    }
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.2,
            "responseMimeType": "application/json"
        }
    }
    
    data = json.dumps(payload).encode("utf-8")
    
    max_retries = 3
    for attempt in range(max_retries + 1):
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=90) as resp:
                body = json.loads(resp.read().decode("utf-8"))
                raw_text = body["candidates"][0]["content"]["parts"][0]["text"].strip()
                # Clean markdown backticks if present
                if raw_text.startswith("```"):
                    raw_text = re.sub(r"^```[a-zA-Z]*\n?", "", raw_text)
                    raw_text = re.sub(r"\n?```$", "", raw_text).strip()
                return json.loads(raw_text)
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8") if hasattr(e, "read") else str(e)
            if e.code in (429, 503) and attempt < max_retries:
                wait_time = 3 * (attempt + 1)
                print(f"[*] Gemini API 503/429 spike. Retrying in {wait_time}s (attempt {attempt+1}/{max_retries})...")
                time.sleep(wait_time)
                continue
            raise RuntimeError(f"HTTP Error {e.code}: {error_body}")
        except Exception as e:
            if attempt < max_retries:
                time.sleep(3)
                continue
            raise RuntimeError(f"Request failed: {e}")

def handle_text_dump(chat_id: int, text: str):
    """Processes a text dump directly into the Second Brain."""
    send_message(chat_id, "🧠 *Memproses text dump dengan Gemini 3.8 Flash...*")
    
    # Save raw to inbox_raw first for provenance
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    raw_filename = f"telegram_{timestamp}.md"
    raw_path = REPO_ROOT / "inbox_raw" / raw_filename
    raw_path.write_text(text, encoding="utf-8")
    
    # Ingest file
    success = ingest.process_file(raw_path)
    if success:
        # Rebuild network index
        vault = graph_index.scan_vault()
        graph_index.build_index_md(vault)
        
        send_message(
            chat_id,
            f"✅ *Catatan Berhasil Masuk ke Second Brain!*\n\n"
            f"📁 *File Raw:* `{raw_filename}`\n"
            f"🔄 *Status:* Ingested, Classified & Network Indexed.\n"
            f"🔗 Buka di VPS / Neovim via `INDEX.md`."
        )
    else:
        send_message(chat_id, "❌ *Gagal memproses catatan.* Silakan periksa log di VPS.")

def handle_voice_note(chat_id: int, file_id: str, mime_type: str = "audio/ogg"):
    """Downloads voice note and triggers multimodal audio ingestion."""
    send_message(chat_id, "🎙️ *Menerima voice note. Mentranskripsikan & menganalisis via Gemini 3.8 Flash...*")
    
    audio_bytes, file_path = download_file(file_id)
    if not audio_bytes:
        send_message(chat_id, "❌ *Gagal mengunduh audio dari Telegram.*")
        return
        
    try:
        import ai_engine
        data, used_model = ai_engine.process_audio_with_ai(audio_bytes, mime_type=mime_type)
        
        # Save note
        slug = data.get("slug", f"voice-{datetime.now().strftime('%Y%m%d%H%M%S')}")
        target_folder = data.get("target_folder", "in_motion/side_builder")
        target_dir = REPO_ROOT / target_folder
        target_dir.mkdir(parents=True, exist_ok=True)
        
        note_file = target_dir / f"{slug}.md"
        note_file.write_text(data.get("formatted_markdown", ""), encoding="utf-8")
        
        # Rebuild network index
        vault = graph_index.scan_vault()
        graph_index.build_index_md(vault)
        
        transcription_snippet = data.get("transcription", "")[:180] + ("..." if len(data.get("transcription", "")) > 180 else "")
        actions = data.get("action_items", [])
        actions_str = "\n".join(actions[:3]) if actions else "_Tidak ada action items._"
        
        reply = (
            f"✅ *Voice Note Berhasil Dikonversi & Dipetakan!*\n"
            f"🤖 *Engine:* `{used_model}`\n\n"
            f"📌 *Judul:* {data.get('title')}\n"
            f"📂 *Folder:* `{target_folder}/{slug}.md`\n"
            f"🏷️ *Stream:* `{data.get('stream')}` | *Type:* `{data.get('type')}`\n\n"
            f"🗣️ *Transkrip:* \n_{transcription_snippet}_\n\n"
            f"⚡ *Action Triggers:*\n{actions_str}\n\n"
            f"🕸️ *Network:* `INDEX.md` telah diperbarui."
        )
        send_message(chat_id, reply)
        
    except Exception as e:
        print(f"[-] Voice note processing error: {e}")
        send_message(chat_id, f"⚠️ *Error saat memproses voice note:* `{e}`\nAudio disimpan ke `inbox_raw/`.")
        # Save audio dump as backup
        backup_path = REPO_ROOT / "inbox_raw" / f"voice_dump_{datetime.now().strftime('%Y%m%d_%H%M%S')}.ogg"
        backup_path.write_bytes(audio_bytes)

def handle_search(chat_id: int, query: str):
    """Executes BM25 search and returns formatted telegram response."""
    if not query.strip():
        send_message(chat_id, "Format: `/search <kata_kunci>`\nContoh: `/search latency benchmark`")
        return
        
    vault = graph_index.scan_vault()
    notes = vault["notes"]
    query_tokens = graph_index.tokenize(query)
    
    import math
    from collections import Counter
    
    doc_tokens = {}
    doc_lens = {}
    df = Counter()
    total_docs = len(notes)

    for path, note in notes.items():
        tokens = graph_index.tokenize(f"{note['title']} {note['body']}")
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
            score += idf * (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * (dl / max(avg_dl, 1))))

        if score > 0:
            scores.append((score, path, note))

    scores.sort(key=lambda x: x[0], reverse=True)
    
    if not scores:
        send_message(chat_id, f"🔍 *Pencarian:* `{query}`\n\n_Tidak ada catatan yang cocok._")
        return
        
    reply = f"🔍 *Hasil Pencarian:* `{query}` (Top {min(3, len(scores))})\n\n"
    for rank, (score, path, note) in enumerate(scores[:3], 1):
        cmd_slug = "/read_" + note["slug"].replace("-", "_")
        reply += f"*{rank}. [[{note['slug']}]]* (Score: `{score:.1f}`)\n"
        reply += f"📁 `{path}`\n"
        snippet = note["body"][:100].replace("\n", " ").strip()
        reply += f"_{snippet}..._\n"
        reply += f"📖 Baca full: {cmd_slug}\n\n"
        
    send_message(chat_id, reply)

def handle_read(chat_id: int, raw_cmd: str):
    """Sends the full content of a requested note directly to Telegram."""
    # Handle both formats: "/read <slug>" and "/read_<slug>"
    query = raw_cmd.strip()
    if query.startswith("/read_"):
        query = query[6:]
    elif query.startswith("/read"):
        query = query[5:].strip()
    elif query.startswith("/baca"):
        query = query[5:].strip()
        
    clean_query = query.replace("_", "-").strip().lower()
    
    if not clean_query:
        send_message(chat_id, "ℹ️ Format: `/read <nama-catatan>` atau ketik `/list` untuk memilih catatan.")
        return

    vault = graph_index.scan_vault()
    notes = vault["notes"]
    
    # 1. Exact match on slug
    matched_note = None
    for note in notes.values():
        if note["slug"].lower() == clean_query:
            matched_note = note
            break
            
    # 2. Fuzzy / partial match on slug or title
    if not matched_note:
        for note in notes.values():
            if clean_query in note["slug"].lower() or clean_query in note["title"].lower():
                matched_note = note
                break
                
    if not matched_note:
        send_message(
            chat_id, 
            f"❌ Catatan `{clean_query}` tidak ditemukan.\n\n"
            f"Ketik `/list` untuk melihat daftar catatan yang tersedia, atau ketik `/search {clean_query}`."
        )
        return

    full_text = matched_note["content"]
    header = (
        f"📄 *{matched_note['title']}*\n"
        f"📁 `{matched_note['path']}`\n"
        f"───────────────\n\n"
    )
    
    # Telegram max message length is 4096. Split into safe chunks of 3800 chars.
    chunk_size = 3800
    if len(full_text) <= chunk_size:
        send_message(chat_id, header + full_text)
    else:
        send_message(chat_id, header)
        for i in range(0, len(full_text), chunk_size):
            chunk = full_text[i:i+chunk_size]
            send_message(chat_id, chunk)

def handle_list(chat_id: int):
    """Lists recent notes in the vault with one-tap /read links."""
    vault = graph_index.scan_vault()
    notes = list(vault["notes"].values())
    
    if not notes:
        send_message(chat_id, "📚 Vault Anda masih kosong.")
        return
        
    # Sort notes alphabetically or by path
    notes.sort(key=lambda x: x["path"])
    
    reply = f"📚 *Daftar Catatan di Second Brain ({len(notes)} catatan):*\n\n"
    for idx, n in enumerate(notes[:20], 1):
        clean_cmd = "/read_" + n["slug"].replace("-", "_")
        reply += f"*{idx}. {n['title']}*\n"
        reply += f"📁 `{n['path']}`\n"
        reply += f"👉 {clean_cmd}\n\n"
        
    reply += "💡 _Klik perintah di atas untuk membaca isi full catatan._"
    send_message(chat_id, reply)

def handle_status(chat_id: int):
    """Returns vault status."""
    vault = graph_index.scan_vault()
    notes = vault["notes"]
    dangling = vault["dangling_links"]
    
    core = sum(1 for n in notes.values() if "core_work" in n["category"])
    side = sum(1 for n in notes.values() if "side_builder" in n["category"])
    lattices = sum(1 for n in notes.values() if "lattices" in n["category"])
    
    reply = (
        f"📊 *Second Brain Vault Status*\n\n"
        f"📚 *Total Notes:* `{len(notes)}`\n"
        f"🏢 *Core Work:* `{core}`\n"
        f"🚀 *Side Builder:* `{side}`\n"
        f"🧱 *Knowledge Lattices:* `{lattices}`\n"
        f"🌱 *Dangling Seeds (Backlog):* `{len(dangling)}`\n\n"
        f"Perintah cepat:\n"
        f"• `/list` -> Daftar semua catatan\n"
        f"• `/search <query>` -> Pencarian catatan"
    )
    send_message(chat_id, reply)

def handle_journal(chat_id: int, raw_text: str):
    """Processes a reflection journal entry adhering to agents.md PROTOKOL 3."""
    journal_content = raw_text.replace("/journal", "", 1).strip()
    if not journal_content:
        send_message(chat_id, "ℹ️ Format: `/journal [isi refleksi atau evaluasi harian]`")
        return
        
    send_message(chat_id, "📝 *Menyimpan dan menganalisis jurnal harian...*")
    today_iso = datetime.now().strftime("%Y-%m-%d")
    
    # Generate short title and summary
    first_line = journal_content.splitlines()[0]
    words = re.findall(r"\w+", first_line)[:5]
    short_slug = "-".join(w.lower() for w in words) if words else "harian"
    short_title = " ".join(words).title() if words else "Refleksi Harian"
    
    filename = f"{today_iso}_{short_slug}.md"
    target_path = REPO_ROOT / "journal" / filename
    
    md_content = f"""---
title: "{short_title}"
date: {today_iso}
type: journal
tags:
  - reflection
  - daily-pulse
links:
  - "[[journal/index]]"
---

# {short_title}

## 1. Refleksi & Catatan Harian
{journal_content}

---

## 2. Analisis & Evaluasi Pola
- Waktu Pencatatan: `{datetime.now().strftime("%Y-%m-%d %H:%M")}`
"""
    target_path.write_text(md_content, encoding="utf-8")
    
    # Update journal/index.md
    j_index = REPO_ROOT / "journal" / "index.md"
    summary_1_sentence = journal_content.replace("\n", " ").strip()[:100] + "..."
    j_entry = f"| {today_iso} | [[{filename[:-3]}\\|{short_title}]] | {summary_1_sentence} |\n"
    if j_index.exists():
        with open(j_index, "a", encoding="utf-8") as f:
            f.write(j_entry)
            
    # Append log.md
    ingest.append_audit_log("JOURNAL", f"journal/{filename}", f"Recorded reflection: {short_title}")
    
    send_message(
        chat_id,
        f"✅ *Jurnal Tersimpan!*\n\n"
        f"📁 `journal/{filename}`\n"
        f"📖 *Indeks Terdaftar:* `journal/index.md`\n"
        f"🔍 Gunakan `/read_{filename[:-3].replace('-', '_')}` untuk membaca ulang."
    )

def handle_crm(chat_id: int, raw_text: str):
    """Processes a CRM profile entry adhering to agents.md PROTOKOL 4."""
    crm_text = raw_text.replace("/crm", "", 1).strip()
    if not crm_text or "-" not in crm_text:
        send_message(chat_id, "ℹ️ Format: `/crm [Nama Lengkap] - [Bio / Peran / Konteks]`\nContoh: `/crm Tiago Forte - Penulis metode PARA & Building a Second Brain`")
        return
        
    parts = crm_text.split("-", 1)
    name = parts[0].strip()
    bio = parts[1].strip()
    
    clean_name_file = name.replace(" ", "-") + ".md"
    target_path = REPO_ROOT / "crm" / clean_name_file
    today_iso = datetime.now().strftime("%Y-%m-%d")
    
    md_content = f"""---
name: "{name}"
role: "Kontak / Jaringan Profesional"
interaction_last_date: {today_iso}
tags:
  - crm
  - professional-network
links:
  - "[[crm/index]]"
---

# {name}

## 1. Bio Singkat & Konteks Relasi
{bio}

---

## 2. Log Interaksi & Catatan
- **{today_iso}**: Profil dicatat via Telegram Second Brain Gateway.
"""
    target_path.write_text(md_content, encoding="utf-8")
    
    # Update crm/index.md
    crm_index = REPO_ROOT / "crm" / "index.md"
    crm_entry = f"| {name} | [[{clean_name_file[:-3]}]] | {bio[:80]} | `[[network]]` |\n"
    if crm_index.exists():
        with open(crm_index, "a", encoding="utf-8") as f:
            f.write(crm_entry)
            
    ingest.append_audit_log("CRM", f"crm/{clean_name_file}", f"Added contact profile for {name}")
    
    send_message(
        chat_id,
        f"👤 *Profil CRM Berhasil Dibuat!*\n\n"
        f"📌 *Nama:* {name}\n"
        f"📁 `crm/{clean_name_file}`\n"
        f"📋 Tercatat di `crm/index.md`."
    )

def handle_compounding_query(chat_id: int, question: str):
    """Executes grounded QA and compounds new reusable insights into wiki/."""
    if not question.strip():
        send_message(chat_id, "ℹ️ Format: `/query [pertanyaan analitis atau sintesis arsitektur]`")
        return
        
    send_message(chat_id, f"🧠 *Menganalisis vault Second Brain untuk:* `{question}`...")
    
    vault = graph_index.scan_vault()
    notes = vault["notes"]
    query_tokens = graph_index.tokenize(question)
    
    # Find relevant context
    scored = []
    for path, n in notes.items():
        score = sum(1 for qt in query_tokens if qt in n["title"].lower() or qt in n["body"].lower())
        if score > 0:
            scored.append((score, n))
    scored.sort(key=lambda x: x[0], reverse=True)
    
    context_text = "\n\n".join([f"--- Catatan: {n['title']} (File: {n['path']}) ---\n{n['body'][:600]}" for _, n in scored[:4]])
    
    prompt = f"""
Pengguna mengajukan pertanyaan analitis berikut:
"{question}"

Gunakan konteks catatan Second Brain berikut untuk menjawab secara grounded:
\"\"\"
{context_text}
\"\"\"

Instruksi:
1. Jawab secara padat, berbasis fakta dalam catatan di atas, sertakan rujukan wikilinks [[slug]].
2. Apakah pertanyaan ini menghasilkan sintesis konsep baru yang bernilai pakai ulang?
Keluarkan JSON:
{{
  "answer": "Jawaban lengkap untuk pengguna",
  "is_new_synthesis": true/false,
  "synthesis_title": "Judul Konsep jika is_new_synthesis true",
  "synthesis_slug": "kebab-case-slug",
  "synthesis_markdown": "Konten Markdown untuk wiki/"
}}
"""
    try:
        import ai_engine
        gemini_key = os.getenv("GEMINI_API_KEY")
        preferred = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.2, "responseMimeType": "application/json"}
        }
        res, model = ai_engine.call_gemini_with_fallback(payload, gemini_key, preferred)
        
        answer = res.get("answer", "Jawaban tidak dapat diformulasikan.")
        send_message(chat_id, f"💡 *Jawaban Ter-grounding:* (via `{model}`)\n\n{answer}")
        
        # PROTOKOL 2: Auto-compound reusable synthesis into wiki/
        if res.get("is_new_synthesis") and res.get("synthesis_slug"):
            s_slug = res.get("synthesis_slug")
            s_title = res.get("synthesis_title", s_slug.replace("-", " ").title())
            s_file = REPO_ROOT / "wiki" / f"{s_slug}.md"
            s_content = res.get("synthesis_markdown", f"# {s_title}\n\n{answer}")
            s_file.write_text(s_content, encoding="utf-8")
            
            ingest.update_index_catalog(s_title, s_slug)
            ingest.append_audit_log("QUERY_COMPOUND", f"wiki/{s_slug}.md", f"Auto-compounded new synthesis from query: {question}")
            send_message(chat_id, f"🌱 *Compounding Insight Baru:* Disimpan ke `wiki/{s_slug}.md` dan dicatat di `index.md`!")
            
    except Exception as e:
        send_message(chat_id, f"⚠️ Gagal memproses query analitis: `{e}`")

def run_bot():
    """Main polling loop."""
    if not BOT_TOKEN:
        print("[!] ERROR: TELEGRAM_BOT_TOKEN is not set in .env!")
        print("[*] Dapatkan token dari @BotFather di Telegram lalu isi di .env.")
        sys.exit(1)
        
    print(f"[*] Starting Second Brain Telegram Gateway Bot...")
    if ALLOWED_USER_ID:
        print(f"[*] Whitelist active: Only Telegram User ID {ALLOWED_USER_ID} is allowed.")
    else:
        print("[!] WARNING: No TELEGRAM_ALLOWED_USER_ID set. Anyone chatting with this bot could ingest notes!")
        
    last_update_id = 0
    
    while True:
        try:
            updates = tg_request("getUpdates", {
                "offset": last_update_id + 1,
                "timeout": 30
            })
            
            for item in updates.get("result", []):
                last_update_id = item["update_id"]
                message = item.get("message")
                if not message:
                    continue
                    
                sender_id = str(message.get("from", {}).get("id", ""))
                chat_id = message.get("chat", {}).get("id")
                
                # Security whitelist check
                if ALLOWED_USER_ID and sender_id != str(ALLOWED_USER_ID):
                    print(f"[-] Unauthorized access attempt from Telegram ID: {sender_id}")
                    send_message(chat_id, f"⛔ *Akses Ditolak.* ID Anda `{sender_id}` belum terdaftar di whitelist.")
                    continue
                    
                # Handle text & commands
                text = message.get("text", "").strip()
                if text.startswith("/start"):
                    send_message(
                        chat_id,
                        "🧠 *Second Brain Telegram Gateway (agents.md Compliant)*\n\n"
                        "Perintah yang Tersedia:\n"
                        "1. *Kirim Teks/Voice Note* -> Otomatis di-ingest.\n"
                        "2. `/journal <refleksi>` -> Catat jurnal harian ke `journal/`.\n"
                        "3. `/crm <Nama> - <Bio>` -> Catat profil kontak ke `crm/`.\n"
                        "4. `/query <pertanyaan>` -> Tanya jawab ter-grounding & auto-compound ke `wiki/`.\n"
                        "5. `/list` -> Daftar catatan dengan link klik.\n"
                        "6. `/read <nama_catatan>` -> Baca isi lengkap catatan.\n"
                        "7. `/search <query>` -> Pencarian semantik BM25.\n"
                        "8. `/status` -> Statistik vault."
                    )
                elif text.startswith("/journal"):
                    handle_journal(chat_id, text)
                elif text.startswith("/crm"):
                    handle_crm(chat_id, text)
                elif text.startswith("/query") or text.startswith("/ask"):
                    handle_compounding_query(chat_id, text.replace("/query", "").replace("/ask", "").strip())
                elif text.startswith("/read") or text.startswith("/baca"):
                    handle_read(chat_id, text)
                elif text.startswith("/list") or text.startswith("/recent"):
                    handle_list(chat_id)
                elif text.startswith("/search"):
                    query = text[7:].strip()
                    handle_search(chat_id, query)
                elif text.startswith("/status"):
                    handle_status(chat_id)
                elif text:
                    handle_text_dump(chat_id, text)
                elif "voice" in message:
                    handle_voice_note(chat_id, message["voice"]["file_id"], mime_type="audio/ogg")
                elif "audio" in message:
                    mime = message["audio"].get("mime_type", "audio/mp3")
                    handle_voice_note(chat_id, message["audio"]["file_id"], mime_type=mime)
                elif "document" in message:
                    # Save document to raw/ for PROTOKOL 1 INGEST
                    doc = message["document"]
                    f_id = doc["file_id"]
                    f_name = doc.get("file_name", f"doc_{int(time.time())}.txt")
                    send_message(chat_id, f"📥 *Menerima dokumen:* `{f_name}`. Memproses ke `raw/`...")
                    file_bytes, _ = download_file(f_id)
                    if file_bytes:
                        raw_save = REPO_ROOT / "raw" / f_name
                        raw_save.write_bytes(file_bytes)
                        success = ingest.ingest_raw_to_wiki(raw_save)
                        if success:
                            send_message(chat_id, f"✅ *Dokumen `{f_name}` berhasil diekstrak ke `wiki/` & diarsipkan ke `raw/processed/`!*")
                        else:
                            send_message(chat_id, f"⚠️ Gagal mengekstrak dokumen `{f_name}`.")
                    
        except KeyboardInterrupt:
            print("\n[*] Bot stopped by user.")
            break
        except Exception as e:
            print(f"[-] Polling error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    try:
        sys.path.insert(0, str(REPO_ROOT))
        from services.telegram_ingest_bot import main as run_new_bot
        run_new_bot()
    except Exception as e:
        print(f"[!] Falling back to legacy runner: {e}")
        run_bot()
