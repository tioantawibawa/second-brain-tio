#!/usr/bin/env python3
"""
Strategic Decision Sparring & Trade-Off Engine.
Compares two competing paths or architectural decisions (Option A vs Option B):
1. Grounds both options using hybrid search in the vault.
2. Evaluates 4 dimensions: Speed, Cognitive Load, Asymmetric Upside, and Fragility Risk.
3. Produces an un-sugarcoated comparison matrix, winner recommendation, and pivot trigger.
4. Operable via CLI & Telegram Bot (/sparring).
"""

import os
import re
import sys
import json
import urllib.request
from pathlib import Path

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

def run_sparring(option_a: str, option_b: str) -> dict:
    """Runs trade-off analysis comparing Option A vs Option B."""
    sys.path.insert(0, str(REPO_ROOT / "tools"))
    try:
        import search
        ctx_a = search.search_vault(option_a, top_k=2, verbose=False)
        ctx_b = search.search_vault(option_b, top_k=2, verbose=False)
    except Exception:
        ctx_a, ctx_b = [], []

    vault_ctx = ""
    if ctx_a:
        vault_ctx += f"\nKonteks Vault untuk '{option_a}':\n" + "\n".join([f"- {h['title']}: {h['content'][:300]}" for h in ctx_a])
    if ctx_b:
        vault_ctx += f"\nKonteks Vault untuk '{option_b}':\n" + "\n".join([f"- {h['title']}: {h['content'][:300]}" for h in ctx_b])

    system_instruction = (
        "Anda adalah Principal System Architect & Strategic Sparring Partner tanpa kompromi.\n"
        "Pengguna sedang menghadapi dilema keputusan antara 2 opsi.\n"
        "Tugas Anda: Bedah kedua opsi secara first-principles dan tentukan pemenang yang paling rasional.\n"
        "Format Output JSON murni dengan key:\n"
        "1. 'core_dilemma': 1 kalimat tesis akar perbedaan kedua opsi.\n"
        "2. 'dimension_comparison': array 4 item (dimension, option_a_verdict, option_b_verdict, winner ('A' atau 'B')) untuk:\n"
        "   - Kecepatan Eksekusi (Time-to-Value)\n"
        "   - Beban Kognitif & Pemeliharaan (Maintenance Burden)\n"
        "   - Asymmetric Upside (Daya Ungkit Jangka Panjang)\n"
        "   - Risiko Kerapuhan & Lock-in (Fragility Risk)\n"
        "3. 'verdict_recommendation': Rekomendasi tegas opsi mana yang harus dipilih dan mengapa.\n"
        "4. 'pivot_condition': Syarat kondisi spesifik kapan pengguna harus segera berpindah opsi (Circuit Breaker)."
    )

    user_prompt = f"""
Opsi A: "{option_a}"
Opsi B: "{option_b}"

{vault_ctx}

Analisis perbandingan trade-off ini secara lugas dan terstruktur. Output JSON valid.
"""

    gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
    groq_key = os.getenv("GROQ_API_KEY", "").strip()
    preferred_model = os.getenv("GEMINI_MODEL", "gemini-3.8-flash").strip()

    # Try Gemini
    if gemini_key:
        models = [preferred_model, "gemini-3.7-flash", "gemini-3.5-flash-lite"]
        for m in models:
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={gemini_key}"
                payload = {
                    "contents": [{"parts": [{"text": f"{system_instruction}\n\n{user_prompt}"}]}],
                    "generationConfig": {"temperature": 0.2, "responseMimeType": "application/json"}
                }
                req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"})
                with urllib.request.urlopen(req, timeout=15) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                    parsed = json.loads(text)
                    parsed["engine"] = f"Gemini ({m})"
                    return parsed
            except Exception:
                continue

    # Try Groq
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
            req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json", "Authorization": f"Bearer {groq_key}"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                parsed = json.loads(data["choices"][0]["message"]["content"])
                parsed["engine"] = "Groq (Llama-3.3-70b)"
                return parsed
        except Exception:
            pass

    # Heuristic fallback
    return {
        "core_dilemma": f"Pertukaran antara kontrol penuh arsitektur ({option_a}) vs efisiensi operasional siap pakai ({option_b}).",
        "dimension_comparison": [
            {"dimension": "Kecepatan Eksekusi", "option_a_verdict": "Memerlukan setup awal lebih lama", "option_b_verdict": "Lebih cepat diluncurkan", "winner": "B"},
            {"dimension": "Beban Kognitif", "option_a_verdict": "Tanggung jawab infrastruktur mandiri", "option_b_verdict": "Dikelola pihak luar", "winner": "B"},
            {"dimension": "Asymmetric Upside", "option_a_verdict": "Kepemilikan IP penuh dan kustomisasi tanpa batas", "option_b_verdict": "Terikat fitur provider", "winner": "A"},
            {"dimension": "Risiko Kerapuhan", "option_a_verdict": "Bebas dari vendor lock-in", "option_b_verdict": "Rentan lonjakan biaya api/layanan", "winner": "A"}
        ],
        "verdict_recommendation": f"Pilih Opsi B ({option_b}) untuk validasi awal. Transisi ke Opsi A ({option_a}) hanya jika skala transaksi telah membenarkan biaya perawatan mandiri.",
        "pivot_condition": "Pindah haluan jika biaya operasional atau batasan teknis melampaui 20% margin proyek.",
        "engine": "Deterministic Sparring Matrix"
    }

def format_sparring_markdown(option_a: str, option_b: str, data: dict) -> str:
    """Formats sparring evaluation into Markdown response."""
    dilemma = data.get("core_dilemma", "")
    dims = data.get("dimension_comparison", [])
    
    dim_text = ""
    for d in dims:
        winner = f"🏆 Pemenang: Opsi {d.get('winner', '-')}"
        dim_text += f"• *{d.get('dimension')}* ({winner})\n"
        dim_text += f"   🅰️ _{d.get('option_a_verdict')}_\n"
        dim_text += f"   🅱️ _{d.get('option_b_verdict')}_\n\n"

    rec = data.get("verdict_recommendation", "")
    pivot = data.get("pivot_condition", "")
    engine = data.get("engine", "AI Sparring Engine")

    reply = (
        f"⚖️ *STRATEGIC DECISION SPARRING*\n"
        f"🅰️ *{option_a}*\n"
        f"        *VS*\n"
        f"🅱️ *{option_b}*\n\n"
        f"📌 *Tesis Dilema Inti:*\n_{dilemma}_\n\n"
        f"📊 *Evaluasi 4 Dimensi Kritis:*\n{dim_text}"
        f"🎯 *Keputusan Rekomendasi:*\n{rec}\n\n"
        f"🛑 *Pivot Trigger (Circuit Breaker):*\n_{pivot}_\n\n"
        f"🤖 _Disintesis via {engine}_"
    )
    return reply

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 tools/sparring.py \"<Opsi A> vs <Opsi B>\"")
        sys.exit(1)
        
    raw_args = " ".join(sys.argv[1:])
    parts = re.split(r"\s+(?:vs|versus)\s+", raw_args, flags=re.IGNORECASE)
    if len(parts) < 2:
        print("[!] Format harus menggunakan 'vs': contoh: 'python3 tools/sparring.py \"Monolith vs Microservices\"'")
        sys.exit(1)
        
    opt_a = parts[0].strip()
    opt_b = parts[1].strip()
    data = run_sparring(opt_a, opt_b)
    print("\n" + "=" * 80)
    print(format_sparring_markdown(opt_a, opt_b, data))
    print("=" * 80 + "\n")

if __name__ == "__main__":
    main()
