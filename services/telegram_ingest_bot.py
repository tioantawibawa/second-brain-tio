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

# ================= 5. Implementation Engines =================

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

async def ptb_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if ALLOWED_USER_ID and user_id != str(ALLOWED_USER_ID):
        await update.message.reply_text(f"⛔ Akses Ditolak. User ID `{user_id}` tidak terdaftar.", parse_mode="Markdown")
        return
    await update.message.reply_text(
        "🧠 *Second Brain Telegram Ingest Bot Active*\n\n"
        "Input yang dapat dikirim langsung:\n"
        "🎙️ *Voice Note / Audio* -> Ditranskripsi ke `raw/voice_dump_*.md` (`#voice-dump`)\n"
        "🔗 *Link Web / YouTube* -> Diekstrak judulnya ke `raw/web_*.md`\n"
        "📝 *Teks Singkat / Ide* -> Disimpan ke `journal/quick_captures.md`",
        parse_mode="Markdown"
    )

async def ptb_handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if ALLOWED_USER_ID and user_id != str(ALLOWED_USER_ID):
        logger.warning(f"Unauthorized text attempt from user {user_id}")
        await update.message.reply_text(f"⛔ Akses Ditolak. User ID `{user_id}` tidak terdaftar.", parse_mode="Markdown")
        return

    text = update.message.text
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
            logger.error(f"Failed to send message: {e}")

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
                    if text == "/start":
                        send_tg_msg(
                            chat_id,
                            "🧠 *Second Brain Telegram Ingest Bot Active*\n\n"
                            "Input yang dapat dikirim langsung:\n"
                            "🎙️ *Voice Note / Audio* -> Ditranskripsi ke `raw/voice_dump_*.md` (`#voice-dump`)\n"
                            "🔗 *Link Web / YouTube* -> Diekstrak judulnya ke `raw/web_*.md`\n"
                            "📝 *Teks Singkat / Ide* -> Disimpan ke `journal/quick_captures.md`"
                        )
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
