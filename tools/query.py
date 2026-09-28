#!/usr/bin/env python3
"""
Grounded Vault Intelligence & Q&A Synthesis Engine (Protokol 2).
Enables querying the Second Brain via natural language:
1. Performs hybrid search (BM25 + Semantic Vector) across all notes.
2. Synthesizes a grounded, executive answer using Gemini / Groq cascade.
3. Cites exact document sources with [[wikilinks]] and /read commands.
4. Operable via CLI and Telegram Bot (/ask).
"""

import os
import re
import sys
import json
import time
import urllib.request
import urllib.error
from pathlib import Path

# UTF-8 stdout protection
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

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

GEMINI_CASCADE = [
    "gemini-3.8-flash",
    "gemini-3.7-flash",
    "gemini-3.6-flash",
    "gemini-3.5-flash-lite",
    "gemini-flash-latest"
]

def search_context_for_query(query: str, top_k: int = 4) -> list[dict]:
    """Retrieves most relevant chunks from hybrid search index."""
    try:
        sys.path.insert(0, str(REPO_ROOT / "tools"))
        import search
        hits = search.search_vault(query, top_k=top_k, verbose=False)
        return hits
    except Exception as e:
        print(f"[!] Hybrid search error: {e}")
        return []

def call_ai_query_synthesis(query: str, hits: list[dict]) -> dict:
    """Calls Gemini or Groq to synthesize an executive grounded answer."""
    gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
    groq_key = os.getenv("GROQ_API_KEY", "").strip()
    preferred_model = os.getenv("GEMINI_MODEL", "gemini-3.8-flash").strip()

    # Build context string
    ctx_blocks = []
    sources = []
    seen_files = set()
    for idx, h in enumerate(hits, 1):
        fp = h.get("file_path", "")
        title = h.get("title", Path(fp).stem)
        content = h.get("content", "")
        ctx_blocks.append(f"--- DOKUMEN {idx}: {title} (Path: {fp}) ---\n{content[:1200]}")
        
        if fp not in seen_files:
            seen_files.add(fp)
            sources.append({
                "title": title,
                "file_path": fp,
                "slug": Path(fp).stem
            })

    context_str = "\n\n".join(ctx_blocks)

    system_instruction = (
        "Anda adalah AI Cognitive Partner & Research Assistant untuk Second Brain pengguna.\n"
        "Tugas Anda: Jawab pertanyaan pengguna SECARA LUGAS, AKURAT, dan TERSTRUKTUR HANYA berdasarkan konteks dokumen vault yang disediakan.\n"
        "Aturan Operasi:\n"
        "1. Bersandar kuat pada fakta di dokumen (Evidence-First). Jangan mengarang data yang tidak ada di dokumen.\n"
        "2. Tuliskan jawaban dalam Bahasa Indonesia profesional dan padat (bullet points, bold untuk terminologi kunci).\n"
        "3. Sertakan rujukan dokumen yang relevan menggunakan format [[Nama Dokumen]].\n"
        "4. Jika informasi pada vault belum lengkap atau tidak membahas aspek tertentu, katakan terus terang apa yang ada dan apa yang belum tercatat.\n"
        "5. Output dalam format JSON murni dengan 3 key:\n"
        "   - 'direct_answer': Jawaban padat (maksimal 3 paragraf atau daftar terstruktur).\n"
        "   - 'key_takeaways': Array 2-3 poin kesimpulan praktis.\n"
        "   - 'action_suggestion': 1 rekomendasi langkah selanjutnya (opsional)."
    )

    user_prompt = f"""
Konteks Dokumen dari Vault Second Brain:
{context_str}

Pertanyaan Pengguna:
"{query}"

Buatlah sintesis jawaban yang grounded dan tajam sesuai instruksi. Output JSON valid.
"""

    # 1. Try Gemini Cascade
    if gemini_key:
        models = [preferred_model] + [m for m in GEMINI_CASCADE if m != preferred_model]
        for m in models:
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={gemini_key}"
                payload = {
                    "contents": [{"parts": [{"text": f"{system_instruction}\n\n{user_prompt}"}]}],
                    "generationConfig": {"temperature": 0.2, "responseMimeType": "application/json"}
                }
                req = urllib.request.Request(
                    url,
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"}
                )
                with urllib.request.urlopen(req, timeout=15) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                    parsed = json.loads(text)
                    parsed["sources"] = sources
                    parsed["engine"] = f"Gemini ({m})"
                    return parsed
            except Exception:
                continue

    # 2. Try Groq Llama-3.3-70b
    if groq_key:
        try:
            url = "https://api.groq.com/openai/v1/chat/completions"
            payload = {
                "model": "llama-3.3-70b-versatile",
                "messages": [
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": user_prompt}
                ],
                "response_format": {"type": "json_object"},
                "temperature": 0.2
            }
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json", "Authorization": f"Bearer {groq_key}"}
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                parsed = json.loads(data["choices"][0]["message"]["content"])
                parsed["sources"] = sources
                parsed["engine"] = "Groq (Llama-3.3-70b)"
                return parsed
        except Exception:
            pass

    # 3. Deterministic Fallback if offline
    summary_lines = []
    for h in hits[:2]:
        summary_lines.append(f"• **{h.get('title', 'Dokumen')}**: {h.get('content', '')[:200]}...")
    
    return {
        "direct_answer": (
            f"Berdasarkan penelusuran dokumen di vault, berikut ringkasan relevan:\n\n" +
            "\n".join(summary_lines)
        ),
        "key_takeaways": [
            "Data disajikan langsung dari potongan teks hasil pencarian hybrid.",
            "AI generation offline; silakan periksa dokumen asli untuk rincian."
        ],
        "action_suggestion": "Buka catatan sumber melalui tautan baca yang tersedia.",
        "sources": sources,
        "engine": "Deterministic Search Extractor"
    }

def ask_vault(query: str, top_k: int = 4) -> dict:
    """Main function to ask a grounded question to the vault."""
    hits = search_context_for_query(query, top_k=top_k)
    if not hits:
        return {
            "query": query,
            "found": False,
            "direct_answer": f"Tidak ditemukan catatan yang relevan dengan pertanyaan '{query}' di dalam vault.",
            "key_takeaways": ["Coba gunakan kata kunci yang lebih umum.", "Gunakan /ingest jika catatan masih berada di folder raw/."],
            "action_suggestion": "Ketik /search untuk mencari dokumen dengan kata kunci alternatif.",
            "sources": [],
            "engine": "Hybrid Index Search"
        }

    res = call_ai_query_synthesis(query, hits)
    res["query"] = query
    res["found"] = True
    return res

def format_query_response_markdown(data: dict) -> str:
    """Formats answer for Telegram or Markdown view."""
    query = data.get("query", "")
    if not data.get("found", False):
        return f"🔍 *Pencarian Pertanyaan:* `{query}`\n\n_Tidak ditemukan dokumen terkait di dalam vault._\n💡 _Coba tanyakan dengan kata kunci yang berbeda atau ketik /list untuk melihat daftar catatan._"

    ans = data.get("direct_answer", "")
    engine = data.get("engine", "AI Engine")
    
    takeaways = data.get("key_takeaways", [])
    takeaways_text = ""
    if takeaways:
        takeaways_text = "\n\n📌 *Intisari Kunci:*\n" + "\n".join([f"• {t}" for t in takeaways])

    rec = data.get("action_suggestion", "")
    rec_text = f"\n\n🎯 *Langkah Tindak Lanjut:*\n_{rec}_" if rec else ""

    sources = data.get("sources", [])
    src_text = ""
    if sources:
        src_text = "\n\n📚 *Sumber Dokumen Vault:*\n"
        for idx, s in enumerate(sources[:3], 1):
            clean_slug = re.sub(r"[^a-zA-Z0-9_]", "_", s["slug"])
            src_text += f"{idx}. *{s['title']}*\n   📁 `{s['file_path']}` 👉 /read_{clean_slug}\n"

    reply = (
        f"💡 *VAULT GROUNDED ANSWER*\n"
        f"❓ *Tanya:* \"{query}\"\n\n"
        f"{ans}"
        f"{takeaways_text}"
        f"{rec_text}"
        f"{src_text}\n"
        f"🤖 _Disintesis via {engine}_"
    )
    return reply

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 tools/query.py \"<pertanyaan Anda>\"")
        sys.exit(1)
        
    query = " ".join(sys.argv[1:])
    print(f"[*] Querying Second Brain for: \"{query}\"...")
    data = ask_vault(query)
    print("\n" + "=" * 80)
    print(format_query_response_markdown(data))
    print("=" * 80 + "\n")

if __name__ == "__main__":
    main()
