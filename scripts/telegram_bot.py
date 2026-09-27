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
    """Sends a message back to the user on Telegram."""
    tg_request("sendMessage", {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode,
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
        data = transcribe_and_ingest_audio(audio_bytes, mime_type=mime_type)
        
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
            f"✅ *Voice Note Berhasil Dikonversi & Dipetakan!*\n\n"
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
        reply += f"*{rank}. [[{note['slug']}]]* (Score: `{score:.1f}`)\n"
        reply += f"📁 `{path}`\n"
        snippet = note["body"][:100].replace("\n", " ").strip()
        reply += f"_{snippet}..._\n\n"
        
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
        f"Ketik `/search <query>` untuk mencari catatan."
    )
    send_message(chat_id, reply)

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
                text = message.get("text", "")
                if text.startswith("/start"):
                    send_message(
                        chat_id,
                        "🧠 *Second Brain Telegram Gateway Aktif!*\n\n"
                        "Kirim apa saja:\n"
                        "1. *Ketik teks ide/transkrip* -> otomatis di-ingest.\n"
                        "2. *Kirim Voice Note (VN)* -> otomatis ditranskripsikan & di-ingest via Gemini 3.8 Flash.\n"
                        "3. `/search <query>` -> BM25 local search langsung dari Telegram.\n"
                        "4. `/status` -> Statistik vault Second Brain."
                    )
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
                    
        except KeyboardInterrupt:
            print("\n[*] Bot stopped by user.")
            break
        except Exception as e:
            print(f"[-] Polling error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    run_bot()
