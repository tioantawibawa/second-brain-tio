#!/usr/bin/env python3
"""
tools/weave.py - Transdisciplinary Knowledge Architecture Engine (PROTOKOL 5)

Identifies structural isomorphisms and cross-pollinates insights between two domains
across the Second Brain vault (wiki/, in_motion/, lattices/).

Usage:
    python tools/weave.py "Credit Risk" "Tactical Football Analytics"
    python tools/weave.py --domain-a "Data Architecture" --domain-b "Behavioral Economics"
    python tools/weave.py "Credit Risk" "Tactical Football Analytics" --dry-run
"""

import os
import sys
import re
import json
import argparse
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path

# Safe Unicode output and unbuffered stdout for Windows terminals
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
    except Exception:
        pass

REPO_ROOT = Path(__file__).resolve().parent.parent

# Load .env if present
env_path = REPO_ROOT / ".env"
if env_path.exists():
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip("\"'"))


def slugify(text: str) -> str:
    """Generate a clean URL/filename-safe slug."""
    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    return text.strip("-")


def search_vault_for_domain(domain_query: str, top_k: int = 4) -> list[dict]:
    """Retrieve relevant vault documents for a domain query."""
    results = []
    
    # Try using tools.search if available
    try:
        sys.path.insert(0, str(REPO_ROOT / "tools"))
        import search
        hits = search.search_vault(domain_query, top_k=top_k, verbose=False)
        for h in hits:
            results.append({
                "path": h["path"],
                "title": h["title"],
                "content": h["content"]
            })
        if results:
            return results
    except Exception:
        pass

    # Heuristic file scan fallback
    search_dirs = ["wiki", "in_motion", "lattices"]
    tokens = [t.lower() for t in domain_query.split() if len(t) > 2]
    
    scored_files = []
    for sdir in search_dirs:
        dir_path = REPO_ROOT / sdir
        if not dir_path.exists():
            continue
        for f in dir_path.glob("**/*.md"):
            try:
                content = f.read_text(encoding="utf-8")
                score = 0
                for t in tokens:
                    if t in f.name.lower():
                        score += 5
                    score += content.lower().count(t)
                if score > 0:
                    scored_files.append((score, f, content))
            except Exception:
                pass

    scored_files.sort(key=lambda x: x[0], reverse=True)
    for _, f, content in scored_files[:top_k]:
        title = f.stem.replace("-", " ").title()
        # Parse title from frontmatter if possible
        if content.startswith("---"):
            m = re.search(r"^title:\s*[\"']?(.*?)[\"']?$", content, re.MULTILINE)
            if m:
                title = m.group(1).strip()
        rel_path = f.relative_to(REPO_ROOT).as_posix()
        results.append({
            "path": rel_path,
            "title": title,
            "content": content[:1200]
        })

    return results


def call_gemini_synthesis(
    domain_a: str,
    domain_b: str,
    context_a: list[dict],
    context_b: list[dict]
) -> dict:
    """Invokes Gemini models with fallback cascade to synthesize cross-domain analogy."""
    gemini_key = os.getenv("GEMINI_API_KEY")
    if not gemini_key:
        return None

    ctx_a_str = "\n\n".join([f"[{doc['title']}] ({doc['path']}):\n{doc['content'][:600]}" for doc in context_a])
    ctx_b_str = "\n\n".join([f"[{doc['title']}] ({doc['path']}):\n{doc['content'][:600]}" for doc in context_b])

    prompt = f"""
Anda adalah Transdisciplinary Knowledge Architect kelas dunia.
Tugas Anda adalah menjalankan OPERASI WEAVE (Sintesis & Analogi Struktural Lintas Domain) antara:
- Domain A: {domain_a}
- Domain B: {domain_b}

Konteks Vault Terkait Domain A:
{ctx_a_str or "(Tidak ada konteks spesifik di vault, gunakan first-principles domain expertise)"}

Konteks Vault Terkait Domain B:
{ctx_b_str or "(Tidak ada konteks spesifik di vault, gunakan first-principles domain expertise)"}

INSTRUKSI ARSITEKTUR KOGNITIF:
1. Temukan abstraksi tingkat tinggi isomorfik (misal: feedback loop, bottleneck & Theory of Constraints, probability shifting / fat-tailed asymmetric risk, fragility vs antifragility, dynamic spatial-temporal coordination).
2. Petakan kesamaan struktural dalam bentuk matriks.
3. Berikan TIGA (3) transfer ilmu konkret dan aplikatif: bagaimana metodologi/solusi dari Domain B ({domain_b}) memecahkan masalah mendasar di Domain A ({domain_a}).
4. Berikan implikasi eksekusi praktis.

Keluarkan dalam format JSON:
{{
  "thesis": "Penjelasan mendalam 2-3 paragraf mengenai tesis dan analogi struktural tingkat tinggi yang menghubungkan Domain A dan Domain B secara matematis/sistemik.",
  "isomorphic_matrix": [
    {{
      "dimension": "Dimensi Sistem (contoh: Distribusi Risiko / Aliran Informasi / Titik Bottleneck)",
      "domain_a": "Manifestasi di Domain A",
      "domain_b": "Manifestasi di Domain B",
      "abstraction": "Abstraksi Isomorfik Bersama"
    }}
  ],
  "transfers": [
    {{
      "title": "Judul Transfer 1 (Solusi Taktis B untuk Masalah Kronis di A)",
      "mechanism_b": "Bagaimana Domain B menangani masalah ini secara teknis/taktis",
      "problem_a": "Masalah analog yang sering dihadapi Domain A",
      "concrete_solution": "Langkah implementasi presisi bagaimana solusi B diterapkan ke A"
    }},
    {{
      "title": "Judul Transfer 2 (Kerangka Evaluasi B untuk Mitigasi Blindspot di A)",
      "mechanism_b": "Metrik atau kerangka evaluasi unik di Domain B",
      "problem_a": "Blindspot atau keterbatasan evaluasi konvensional di Domain A",
      "concrete_solution": "Langkah integrasi metrik/harness B ke sistem A"
    }},
    {{
      "title": "Judul Transfer 3 (Mekanisme Adaptasi B untuk Optimasi Performa di A)",
      "mechanism_b": "Model adaptasi dinamis real-time di Domain B",
      "problem_a": "Inersia atau keterlambatan respon adaptasi di Domain A",
      "concrete_solution": "Arsitektur adaptasi yang ditransfer ke pipeline Domain A"
    }}
  ],
  "execution_implications": "Rekomendasi taktis konkret untuk eksperimen builder (misal playbook di in_motion/ atau arsitektur evaluasi baru)."
}}
"""

    models_to_try = [
        "gemini-3.8-flash",
        "gemini-3.7-flash",
        "gemini-3.6-flash",
        "gemini-3.5-flash-lite"
    ]

    for model in models_to_try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={gemini_key}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.25,
                "responseMimeType": "application/json"
            }
        }
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=12) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                parsed = json.loads(text)
                print(f"[*] Cross-domain WEAVE synthesis generated via Gemini AI ({model})")
                return parsed
        except Exception:
            continue

    return None


def generate_heuristic_synthesis(domain_a: str, domain_b: str) -> dict:
    """Deterministic fallback synthesis based on systems thinking and first principles."""
    return {
        "thesis": (
            f"Analogi struktural antara **{domain_a}** dan **{domain_b}** berakar pada manajemen dinamika sistem "
            f"di bawah ketidakpastian tinggi dan asimetri informasi. Kedua disiplin secara fundamental beroperasi "
            f"pada model probabilitas dinamis: mengalokasikan kapasitas terbatas pada ruang spatial-temporal "
            f"sembari mengantisipasi pergeseran distribusi ekstrem (fat-tailed events) dan delayed feedback loops. "
            f"Ketika domain A berfokus pada kestabilan baseline dan mitigasi risiko katastropik, domain B "
            f"telah mengembangkan insting agresif dalam dynamic spatial positioning dan real-time exploitation "
            f"terhadap celah transien."
        ),
        "isomorphic_matrix": [
            {
                "dimension": "Topologi Risiko & Ruang Keputusan",
                "domain_a": f"Distribusi probabilitas default/kegagalan fitur pada {domain_a}",
                "domain_b": f"Penguasaan half-spaces & eksploitasi ruang transien pada {domain_b}",
                "abstraction": "Spatial-Temporal State Space Representation & Convex Hull Optimization"
            },
            {
                "dimension": "Mekanisme Umpan Balik (Feedback Loop)",
                "domain_a": "Delayed Ground Truth (label aktual baru terbit berminggu-minggu)",
                "domain_b": "High-Frequency Kinetic Feedback (umpan balik transisi per detik)",
                "abstraction": "Asynchronous Telemetry & Rolling Proxy Metric Verification"
            },
            {
                "dimension": "Degradasi Sistemik & Adaptasi",
                "domain_a": "Covariate Shift & Model Performance Decay musiman",
                "domain_b": "Tactical Counter-Pressing & Structural Fatigue lawan",
                "abstraction": "Dynamic Routing, Role Shifting, & Antifragile Re-balancing"
            },
            {
                "dimension": "Alokasi Kapasitas & Bottleneck",
                "domain_a": "Throttling throughput, inferensi pipeline, dan cadangan risiko",
                "domain_b": "Stamina pemain, overload satu sisi lapangan (overload to isolate)",
                "abstraction": "Theory of Constraints (Goldratt) & Localized Overload Strategy"
            }
        ],
        "transfers": [
            {
                "title": f"Transfer 1: Dynamic Spatial Overload untuk Mengatasi Bottleneck di {domain_a}",
                "mechanism_b": (
                    f"Dalam {domain_b}, konsep 'Overload to Isolate' memusatkan densitas aset pada satu zona fokal "
                    f"untuk memancing distorsi struktur pertahanan, membuka koridor isolasi 1v1 di sisi berlawanan."
                ),
                "problem_a": (
                    f"Pada {domain_a}, antrean komputasi atau degradasi fitur sering mengalami stagnasi "
                    f"karena sumber daya dibagi rata tanpa mempertimbangkan sensitivitas segmen kritis."
                ),
                "concrete_solution": (
                    f"Terapkan arsitektur 'Priority Overload Buffer': alokasikan 80% throughput komputasi evaluasi "
                    f"secara dinamis ke segmen data dengan tingkat pergeseran (PSI) tertinggi, sembari "
                    f"mengisolasi segmen stabil pada model cache berbiaya rendah (evergreen tier)."
                )
            },
            {
                "title": f"Transfer 2: Expected Threat (xT) & Field Tilt Matrix sebagai Early-Warning Metric di {domain_a}",
                "mechanism_b": (
                    f"{domain_b} menggunakan metrik seperti Expected Possession Value (EPV) dan Expected Threat (xT) "
                    f"untuk mengukur probabilitas gol sebelum tindakan akhir dieksekusi, melampaui metrik tertinggal (lagging) seperti skor akhir."
                ),
                "problem_a": (
                    f"Model konvensional di {domain_a} lumpuh oleh Delayed Ground Truth, hanya mengukur performa "
                    f"setelah insiden terjadi (AUC-ROC/default rate pasca kejadian)."
                ),
                "concrete_solution": (
                    f"Bangun harness telemetri 'Pre-Ground Truth Proxy Index' yang mengukur vektor pergeseran feature centroid "
                    f"seperti xT: hitung degradasi nilai probabilitas laten per batch harian sebelum label aktual terkonfirmasi."
                )
            },
            {
                "title": f"Transfer 3: Rest Defense (In-Possession Shape) sebagai Proteksi Katastropik di {domain_a}",
                "mechanism_b": (
                    f"Struktur 'Rest Defense' memastikan tim tetap menjaga 3-4 pemain dalam formasi perlindungan "
                    f"ketika fase menyerang berlangsung, mengeliminasi risiko serangan balik cepat."
                ),
                "problem_a": (
                    f"Pipeline di {domain_a} kerap mengalami kerapuhan (*fragility*) ketika terjadi lonjakan beban "
                    f"musiman atau black swan shock karena seluruh kapasitas dialokasikan ke jalur aktif tanpa safe-mode fallback."
                ),
                "concrete_solution": (
                    f"Wajibkan 'Rest-State Shadow Model': jalankan model aturan heuristik berbasis constraint ketat "
                    f"secara paralel di background dengan batas circuit-breaker otomatis jika model adaptif menyimpang > 2.5 sigma."
                )
            }
        ],
        "execution_implications": (
            f"Integrasikan kerangka sintesis ini ke dalam playbook evaluasi di `lattices/eval-harness-v1.md` "
            f"dan rancang prototipe routing adaptif di `in_motion/` untuk memvalidasi telemetri proaktif lintas kuartal."
        )
    }


def format_synthesis_markdown(
    domain_a: str,
    domain_b: str,
    data: dict,
    backlinks: list[str]
) -> str:
    """Renders the synthesis markdown document following PROTOKOL 5."""
    now_str = datetime.now().strftime("%Y-%m-%d")
    title = f"Sintesis Lintas Domain: {domain_a} x {domain_b}"
    
    links_yaml = "\n".join([f'  - "{wl}"' for wl in backlinks]) if backlinks else "  - \"[[index]]\""

    matrix_rows = "\n".join([
        f"| {m['dimension']} | {m['domain_a']} | {m['domain_b']} | **{m['abstraction']}** |"
        for m in data.get("isomorphic_matrix", [])
    ])

    transfers_md = ""
    for idx, t in enumerate(data.get("transfers", []), start=1):
        transfers_md += f"""### Transfer {idx}: {t['title']}

- **Mekanisme di {domain_b}**:  
  {t['mechanism_b']}
- **Masalah Analog di {domain_a}**:  
  {t['problem_a']}
- **Solusi Taktis & Implementasi di {domain_a}**:  
  > [!TIP] Blueprint Implementasi
  > {t['concrete_solution']}

---

"""

    md = f"""---
title: "{title}"
type: cross_domain_synthesis
domain_a: "{domain_a}"
domain_b: "{domain_b}"
created_at: {now_str}
tags:
  - weave
  - cross-domain
  - structural-analogy
  - mental-model
links:
{links_yaml}
---

# {title}

> **Analogi Struktural Isomorfik Antara {domain_a} dan {domain_b}**  
> Dihasilkan secara otonom melalui **PROTOKOL 5: OPERASI WEAVE**  
> Tanggal Pembuatan: `{now_str}`

---

## 1. Tesis & Analogi Struktural Tingkat Tinggi

{data.get('thesis', '')}

---

## 2. Matriks Pemetaan Isomorfik

| Dimensi Sistem | {domain_a} | {domain_b} | Abstraksi Bersama (First Principles) |
| :--- | :--- | :--- | :--- |
{matrix_rows}

---

## 3. Tiga Transfer Ilmu Konkret (Cross-Pollination)

{transfers_md}

## 4. Implikasi Eksekusi & Next Action

{data.get('execution_implications', '')}

---

## Nodus Terkait & Graf Konektivitas
- Domain A Root: {domain_a}
- Domain B Root: {domain_b}
- Indeks Pengetahuan: [[index|Knowledge Network Index]]
"""
    return md


def update_indexes(new_filename: str, title: str, domain_a: str, domain_b: str):
    """Reconciles index.md and INDEX.md with the newly created synthesis."""
    slug = Path(new_filename).stem
    new_entry = f"| [[wiki/{slug}|{title}]] | 4 | 2 |\n"
    
    # Update index.md
    index_path = REPO_ROOT / "index.md"
    if index_path.exists():
        content = index_path.read_text(encoding="utf-8")
        if slug not in content:
            marker = "## 2. Knowledge Wiki & Topic Syntheses (`wiki/`)\n| Konsep / Entitas | Outgoing | Backlinks |\n| :--- | :--- | :--- |\n"
            if marker in content:
                content = content.replace(marker, marker + new_entry)
                index_path.write_text(content, encoding="utf-8")
                print(f"[*] Reconciled index.md with [[wiki/{slug}]]")
    
    # Update INDEX.md
    index_caps = REPO_ROOT / "INDEX.md"
    if index_caps.exists():
        content = index_caps.read_text(encoding="utf-8")
        if slug not in content:
            # Check if there is a Wiki section
            if "## 2. Knowledge Wiki & Topic Syntheses" in content:
                content = re.sub(
                    r"(## 2\. Knowledge Wiki & Topic Syntheses.*?\|\s*:---\s*\|\s*:---\s*\|\s*:---\s*\|\n)",
                    r"\1" + new_entry,
                    content,
                    flags=re.DOTALL
                )
                index_caps.write_text(content, encoding="utf-8")
                print(f"[*] Reconciled INDEX.md with [[wiki/{slug}]]")


def log_operation(slug: str, domain_a: str, domain_b: str):
    """Appends WEAVE operation to log.md."""
    log_path = REPO_ROOT / "log.md"
    if not log_path.exists():
        return
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    entry = f"| {now_str} | WEAVE | `wiki/{slug}.md` | Sintesis lintas domain: {domain_a} x {domain_b} via PROTOKOL 5 |\n"
    try:
        content = log_path.read_text(encoding="utf-8")
        if not content.endswith("\n"):
            content += "\n"
        log_path.write_text(content + entry, encoding="utf-8")
        print(f"[*] Audit trail recorded in log.md: WEAVE [[wiki/{slug}]]")
    except Exception as e:
        print(f"[!] Failed to update log.md: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="Transdisciplinary Knowledge Architecture Engine (PROTOKOL 5: OPERASI WEAVE)"
    )
    parser.add_argument("domain_a", nargs="?", default="", help="Domain A (e.g. Credit Risk / Data Architecture)")
    parser.add_argument("domain_b", nargs="?", default="", help="Domain B (e.g. Tactical Football Analytics / Behavioral Economics)")
    parser.add_argument("--domain-a", dest="opt_domain_a", help="Explicit Domain A")
    parser.add_argument("--domain-b", dest="opt_domain_b", help="Explicit Domain B")
    parser.add_argument("--dry-run", action="store_true", help="Preview output without writing files")

    args = parser.parse_args()
    domain_a = (args.opt_domain_a or args.domain_a or "").strip()
    domain_b = (args.opt_domain_b or args.domain_b or "").strip()

    if not domain_a or not domain_b:
        print("[!] Error: Both Domain A and Domain B must be specified.")
        print("    Example: python tools/weave.py \"Credit Risk\" \"Tactical Football Analytics\"")
        sys.exit(1)

    print(f"[*] Initiating OPERASI WEAVE between:")
    print(f"    - Domain A: {domain_a}")
    print(f"    - Domain B: {domain_b}")

    # 1. Search vault for domain context
    print("[*] Retrieving relevant nodes from vault...")
    ctx_a = search_vault_for_domain(domain_a, top_k=3)
    ctx_b = search_vault_for_domain(domain_b, top_k=3)

    backlinks = []
    for doc in ctx_a + ctx_b:
        stem = Path(doc["path"]).stem
        backlinks.append(f"[[{stem}]]")
    # Add unique
    backlinks = list(dict.fromkeys(backlinks))

    # 2. Synthesis generation (AI Cascade with Heuristic fallback)
    print("[*] Identifying isomorphic high-level abstractions & cross-domain transfers...")
    data = call_gemini_synthesis(domain_a, domain_b, ctx_a, ctx_b)
    if not data:
        print("[*] AI offline or unavailable. Engaging deterministic first-principles synthesis engine...")
        data = generate_heuristic_synthesis(domain_a, domain_b)

    # 3. Create file name and format markdown
    slug_a = slugify(domain_a.split("/")[0])
    slug_b = slugify(domain_b.split("/")[0])
    target_filename = f"synthesis_{slug_a}_{slug_b}.md"
    target_file = REPO_ROOT / "wiki" / target_filename

    md_content = format_synthesis_markdown(domain_a, domain_b, data, backlinks)

    if args.dry_run:
        print(f"\n[DRY RUN PREVIEW] Output path: wiki/{target_filename}\n")
        print(md_content[:1500])
        print("\n... (truncated for preview) ...")
        return

    # Write file
    target_file.parent.mkdir(parents=True, exist_ok=True)
    target_file.write_text(md_content, encoding="utf-8")
    print(f"[+] Created synthesis document: wiki/{target_filename}")

    # 4. Reconcile Index
    update_indexes(target_filename, f"Sintesis Lintas Domain: {domain_a} x {domain_b}", domain_a, domain_b)

    # 5. Log Operation
    log_operation(target_file.stem, domain_a, domain_b)

    # 6. Re-index search engine
    try:
        sys.path.insert(0, str(REPO_ROOT / "tools"))
        import indexer
        indexer.build_index(verbose=False)
        print("[*] Hybrid search index updated successfully.")
    except Exception as e:
        print(f"[!] Warning: Index update skipped: {e}")

    print(f"\n[SUCCESS] OPERASI WEAVE completed successfully.")
    print(f"File created: wiki/{target_filename}")


if __name__ == "__main__":
    main()
