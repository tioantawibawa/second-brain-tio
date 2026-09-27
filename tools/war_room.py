#!/usr/bin/env python3
"""
tools/war_room.py - Red Team Adversary & Decision Pre-Mortem Engine (PROTOKOL 6)

Simulates a high-stakes "War Room Pre-Mortem" for a critical decision or project.
Scans:
  1. journal/ for past cognitive biases, over-commitment, and high-stress points.
  2. crm/ for network sounding boards and domain specialists.
  3. wiki/ & lattices/ for technical assumptions, latency limits, and fragility risks.

Generates:
  in_motion/war_room_[nama_proyek].md
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
    """Generate a clean slug for file naming."""
    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "_", text)
    return text.strip("_")


def scan_journal_biases() -> list[dict]:
    """Scans journal/ for past cognitive friction, over-commitment, and stressors."""
    journal_dir = REPO_ROOT / "journal"
    if not journal_dir.exists():
        return []

    biases = []
    for f in journal_dir.glob("*.md"):
        if f.name == "index.md":
            continue
        try:
            content = f.read_text(encoding="utf-8")
            # Look for stress patterns, reflection notes, and cognitive bottlenecks
            title_m = re.search(r"^title:\s*[\"']?(.*?)[\"']?$", content, re.MULTILINE)
            title = title_m.group(1).strip() if title_m else f.stem
            biases.append({
                "file": f"journal/{f.name}",
                "title": title,
                "snippet": content[:800]
            })
        except Exception:
            pass
    return biases


def scan_crm_contacts() -> list[dict]:
    """Scans crm/ for advisors, specialists, and network sounding boards."""
    crm_dir = REPO_ROOT / "crm"
    if not crm_dir.exists():
        return []

    contacts = []
    for f in crm_dir.glob("*.md"):
        if f.name == "index.md":
            continue
        try:
            content = f.read_text(encoding="utf-8")
            title_m = re.search(r"^title:\s*[\"']?(.*?)[\"']?$", content, re.MULTILINE)
            name = title_m.group(1).strip() if title_m else f.stem.replace("-", " ")
            role_m = re.search(r"^role:\s*[\"']?(.*?)[\"']?$", content, re.MULTILINE)
            role = role_m.group(1).strip() if role_m else "Subject Matter Expert"
            contacts.append({
                "file": f"crm/{f.name}",
                "name": name,
                "role": role,
                "snippet": content[:500]
            })
        except Exception:
            pass
    return contacts


def scan_technical_assumptions(decision: str) -> list[dict]:
    """Scans wiki/ and lattices/ for technical architecture and fragility assumptions."""
    results = []
    try:
        sys.path.insert(0, str(REPO_ROOT / "tools"))
        import search
        hits = search.search_vault(decision, top_k=4, verbose=False)
        for h in hits:
            results.append({
                "file": h["path"],
                "title": h["title"],
                "snippet": h["content"][:600]
            })
        if results:
            return results
    except Exception:
        pass

    # Heuristic fallback
    for folder in ["wiki", "lattices"]:
        p = REPO_ROOT / folder
        if not p.exists():
            continue
        for f in p.glob("**/*.md"):
            try:
                txt = f.read_text(encoding="utf-8")
                results.append({
                    "file": f"{folder}/{f.name}",
                    "title": f.stem,
                    "snippet": txt[:500]
                })
                if len(results) >= 4:
                    break
            except Exception:
                pass
    return results


def call_gemini_war_room(
    decision: str,
    journals: list[dict],
    crms: list[dict],
    tech_notes: list[dict]
) -> dict:
    """Calls Gemini with red-team adversary persona."""
    gemini_key = os.getenv("GEMINI_API_KEY")
    if not gemini_key:
        return None

    journal_ctx = "\n\n".join([f"[{j['title']} - {j['file']}]:\n{j['snippet']}" for j in journals])
    crm_ctx = "\n\n".join([f"[{c['name']} ({c['role']}) - {c['file']}]:\n{c['snippet']}" for c in crms])
    tech_ctx = "\n\n".join([f"[{t['title']} - {t['file']}]:\n{t['snippet']}" for t in tech_notes])

    prompt = f"""
Anda adalah Red Team Adversary & Decision Strategist kelas dunia.
Tugas Anda adalah membedah dan menghancurkan bias optimisme dari keputusan/proyek berikut melalui simulasi "War Room Pre-Mortem".

KEPUTUSAN / PROYEK YANG DIUJI:
"{decision}"

GROUNDING DARI SECOND BRAIN USER:
=== 1. Riwayat Jurnal, Bias Kognitif & Titik Stres Masa Lalu ===
{journal_ctx or "_Tidak ada catatan jurnal._"}

=== 2. Jaringan CRM & Subject Matter Experts ===
{crm_ctx or "_Tidak ada data kontak CRM._"}

=== 3. Asumsi Teknis & Arsitektur dari Wiki / Lattices ===
{tech_ctx or "_Tidak ada dokumen teknis terkait._"}

INSTRUKSI WAR ROOM:
Bayangkan skenario terburuk: Kita berada di 6-12 bulan ke depan, dan proyek/keputusan ini telah GAGAL TOTAL secara memalukan, menghabiskan modal/waktu, dan merusak reputasi/kesehatan mental.
Tugas Anda adalah menjelaskan retrospektif mengapa ini terjadi tanpa kompromi (zero-sugarcoating).

Keluarkan dalam format JSON:
{{
  "project_title": "Judul resmi keputusan/proyek",
  "executive_premortem_thesis": "Analisis retrospektif 2 paragraf yang tajam mengapa proyek ini gagal dari masa depan.",
  "failure_modes": [
    {{
      "scenario": "Nama Skenario Kegagalan 1 (misal: Silent Pipeline Poisoning / Latency Avalanche)",
      "probability": "Tinggi / Menengah / Kritis",
      "mechanism": "Rantai sebab-akibat teknis dan psikologis bagaimana kegagalan ini berkembang biak tanpa disadari.",
      "trigger_event": "Peristiwa pemicu awal (leading indicator) yang diabaikan."
    }},
    {{
      "scenario": "Nama Skenario Kegagalan 2",
      "probability": "Tinggi / Menengah / Kritis",
      "mechanism": "Rantai sebab-akibat.",
      "trigger_event": "Peristiwa pemicu awal."
    }},
    {{
      "scenario": "Nama Skenario Kegagalan 3",
      "probability": "Tinggi / Menengah / Kritis",
      "mechanism": "Rantai sebab-akibat.",
      "trigger_event": "Peristiwa pemicu awal."
    }}
  ],
  "unstated_assumptions": [
    {{
      "assumption": "Asumsi terselubung yang dianggap benar tanpa pembuktian data.",
      "flaw": "Mengapa asumsi ini rapuh atau cacat secara fundamental.",
      "reality_check": "Fakta lapangan atau batasan teknis riil yang membantahnya."
    }},
    {{
      "assumption": "Asumsi terselubung 2",
      "flaw": "Mengapa rapuh.",
      "reality_check": "Fakta lapangan."
    }},
    {{
      "assumption": "Asumsi terselubung 3",
      "flaw": "Mengapa rapuh.",
      "reality_check": "Fakta lapangan."
    }}
  ],
  "blindspot_questions": [
    "Pertanyaan tajam 1 yang wajib dijawab sebelum commit modal/waktu.",
    "Pertanyaan tajam 2",
    "Pertanyaan tajam 3",
    "Pertanyaan tajam 4",
    "Pertanyaan tajam 5"
  ],
  "actionable_mitigations": [
    {{
      "action": "Langkah mitigasi preventif konkret 1 (Kill-Switch / Shadow Harness / SLA hard ceiling)",
      "responsible_guardrail": "Mekanisme pengaman teknis atau batasan operasional yang dipasang",
      "metric_threshold": "Threshold angka kuantitatif untuk mematikan proyek (misal: PSI > 0.25, Latensi > 1500ms, Error > 2%)"
    }},
    {{
      "action": "Langkah mitigasi preventif 2",
      "responsible_guardrail": "Mekanisme pengaman",
      "metric_threshold": "Threshold kuantitatif"
    }},
    {{
      "action": "Langkah mitigasi preventif 3",
      "responsible_guardrail": "Mekanisme pengaman",
      "metric_threshold": "Threshold kuantitatif"
    }}
  ],
  "advisory_links": [
    "Rekomendasi nama tokoh dari CRM atau disiplin eksternal yang wajib diajak bicara untuk sanity check"
  ]
}}
"""

    models = ["gemini-3.8-flash", "gemini-3.7-flash", "gemini-3.5-flash-lite"]
    for model in models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={gemini_key}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.3, "responseMimeType": "application/json"}
        }
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=14) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                parsed = json.loads(text)
                print(f"[*] Red Team War Room analysis synthesized via Gemini ({model})")
                return parsed
        except Exception:
            continue

    # Tier 2: Groq Llama-3.3-70b Fallback
    groq_key = os.getenv("GROQ_API_KEY")
    if groq_key:
        try:
            url = "https://api.groq.com/openai/v1/chat/completions"
            payload = {
                "model": "llama-3.3-70b-versatile",
                "messages": [{"role": "user", "content": prompt}],
                "response_format": {"type": "json_object"},
                "temperature": 0.3
            }
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json", "Authorization": f"Bearer {groq_key}"}
            )
            with urllib.request.urlopen(req, timeout=18) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                text = data["choices"][0]["message"]["content"].strip()
                parsed = json.loads(text)
                print("[*] Red Team War Room analysis synthesized via Groq (llama-3.3-70b)")
                return parsed
        except Exception:
            pass

    return None


def generate_heuristic_war_room(decision: str, journals: list[dict], crms: list[dict]) -> dict:
    """Deterministic fallback for high-stakes Red Team analysis."""
    return {
        "project_title": decision,
        "executive_premortem_thesis": (
            f"Retrospektif dari masa depan: Inisiatif '{decision}' gagal bukan karena kurangnya kecerdasan "
            f"atau ambisi, melainkan akibat 'Builder's Hyper-Optimism' yang mengabaikan friksi operasional, "
            f"beban kognitif konkurensi ganda, dan delayed feedback loop. Tim terperangkap dalam ilusi bahwa "
            f"arsitektur baru akan menyelesaikan kompleksitas teknis, padahal justru melipatgandakan titik kerapuhan "
            f"dan ketergantungan sistemik."
        ),
        "failure_modes": [
            {
                "scenario": "Silent Degradation & Delayed Truth Poisoning",
                "probability": "Kritis",
                "mechanism": (
                    "Sistem baru berjalan normal di permukaan, namun data atau skor laten mengalami degradasi drift "
                    "yang baru terdeteksi berminggu-minggu kemudian setelah pelanggan/stakeholder komplain."
                ),
                "trigger_event": "Mengabaikan telemetri unsupervised pra-ground truth (seperti PSI atau Wasserstein distance)."
            },
            {
                "scenario": "Cognitive Bandwidth Bankruptcy (Over-Commitment Crash)",
                "probability": "Tinggi",
                "mechanism": (
                    "Sesuai pola yang terdokumentasi di journal/, pengerjaan inisiatif baru ini menuntut "
                    "pemantauan manual intensif yang mengkanibalisasi energi proyek inti lainnya hingga seluruh lini mandek."
                ),
                "trigger_event": "Ketiadaan single-click capture dan otomatisasi alarm kegagalan sejak hari pertama."
            },
            {
                "scenario": "Operational Latency & Dependency Chokepoint",
                "probability": "Tinggi",
                "mechanism": (
                    "Komponen upstream pihak ketiga atau dependensi asynchronous mengalami throttling, "
                    "menyebabkan cascading failure ke seluruh endpoint konsumen."
                ),
                "trigger_event": "P99 latency melonjak 3x lipat tanpa ada circuit breaker otomatis."
            }
        ],
        "unstated_assumptions": [
            {
                "assumption": "Kualitas dan format data input downstream akan selalu konsisten dengan baseline.",
                "flaw": "Data musiman, anomali payload, dan update format upstream terjadi tanpa pemberitahuan.",
                "reality_check": "Distribusi data live di produksi selalu mengalami pergeseran kovariat (covariate shift)."
            },
            {
                "assumption": "Anda memiliki bandwidth kognitif untuk mengawasi operasional harian secara manual.",
                "flaw": "Refleksi di journal/ membuktikan bahwa working memory Anda cepat tersaturasi saat switching konteks.",
                "reality_check": "Jika sistem tidak memiliki autonomous self-healing, sistem akan ditinggalkan."
            },
            {
                "assumption": "Stakeholder dan pengguna langsung mengadopsi output baru tanpa resistensi.",
                "flaw": "Inersia operasional manusia selalu menolak perubahan antarmuka tanpa validasi paralel yang lama.",
                "reality_check": "Adopsi butuh dual-run shadow mode minimal 2-4 minggu sebelum cutover total."
            }
        ],
        "blindspot_questions": [
            "Apa satu metrik obyektif yang jika turun 15% membuktikan keputusan ini harus segera dibatalkan?",
            "Siapa orang pertama yang paling dirugikan jika inisiatif ini mengalami downtime 48 jam?",
            "Berapa jam per minggu yang benar-benar tersisa untuk memelihara proyek ini setelah dikurangi komitmen inti?",
            "Apakah ada solusi 20% tenaga yang memberikan 80% dampak tanpa harus membangun arsitektur baru dari nol?",
            "Bagaimana rencana rollback 15 menit jika sistem baru meledak saat deployment hari Jumat sore?"
        ],
        "actionable_mitigations": [
            {
                "action": "Shadow Mode Deployment & Dual-Run Architecture",
                "responsible_guardrail": "Jalankan sistem baru secara paralel dengan sistem lama tanpa mempengaruhi output produksi langsung.",
                "metric_threshold": "Validasi konsistensi 99.5% selama 14 hari berturut-turut sebelum migrasi penuh."
            },
            {
                "action": "Hard Circuit Breaker & Fallback Automation",
                "responsible_guardrail": "Pasang trigger otomatis yang mengembalikan rute ke sistem baseline jika error terdeteksi.",
                "metric_threshold": "Error rate > 1.5% atau latensi P99 > 2000ms dalam rentang 5 menit."
            },
            {
                "action": "Pre-Mortem Sanity Check dengan External Sounding Board",
                "responsible_guardrail": "Jadwalkan review kritis 30 menit dengan pakar relevan di jaringan CRM sebelum eksekusi.",
                "metric_threshold": "Wajib mendapatkan minimal 2 catatan 'veto' kritis yang terselesaikan sebelum go-live."
            }
        ],
        "advisory_links": [
            "Konsultasikan dengan profil CRM atau spesialis arsitektur terkait untuk memvalidasi batasan sistemik."
        ]
    }


def format_war_room_markdown(
    decision: str,
    data: dict,
    journals: list[dict],
    crms: list[dict],
    tech_notes: list[dict]
) -> str:
    """Formats the War Room Pre-Mortem report markdown."""
    now_str = datetime.now().strftime("%Y-%m-%d")
    clean_title = data.get("project_title", decision)
    slug = slugify(clean_title)

    # Format Failure Modes
    failure_rows = ""
    for idx, fm in enumerate(data.get("failure_modes", []), start=1):
        failure_rows += f"""### Skenario {idx}: {fm['scenario']} (`Probabilitas: {fm.get('probability', 'Tinggi')}`)
- **Rantai Kausalitas (Mechanism)**:  
  {fm['mechanism']}
- **Leading Indicator / Trigger Event**:  
  > [!WARNING] Tanda Bahaya Awal
  > {fm['trigger_event']}

---

"""

    # Format Unstated Assumptions
    assump_rows = ""
    for idx, ua in enumerate(data.get("unstated_assumptions", []), start=1):
        assump_rows += f"""| {idx} | **{ua['assumption']}** | {ua['flaw']} | `{ua['reality_check']}` |
"""

    # Format Blindspot Questions
    questions_rows = ""
    for idx, q in enumerate(data.get("blindspot_questions", []), start=1):
        questions_rows += f"""{idx}. **{q}**\n"""

    # Format Actionable Mitigation
    mitig_rows = ""
    for idx, am in enumerate(data.get("actionable_mitigations", []), start=1):
        mitig_rows += f"""### Mitigasi {idx}: {am['action']}
- **Mekanisme Guardrail**: {am['responsible_guardrail']}
- **Ambang Batas Kuantitatif (Kill-Switch Threshold)**:  
  > [!IMPORTANT] Threshold Batas Toleransi
  > `{am['metric_threshold']}`

---

"""

    # Traces
    journal_links = "\n".join([f"- [[{j['file'].replace('.md', '')}|{j['title']}]]" for j in journals]) or "- _Tidak ada grounding jurnal._"
    crm_links = "\n".join([f"- [[{c['file'].replace('.md', '')}|{c['name']}]] ({c['role']})" for c in crms]) or "- _Tidak ada sounding board terdaftar._"
    tech_links = "\n".join([f"- [[{t['file'].replace('.md', '')}|{t['title']}]]" for t in tech_notes]) or "- _Tidak ada referensi teknis._"

    md = f"""---
title: "War Room Pre-Mortem: {clean_title}"
type: war_room_pre_mortem
status: active
decision_target: "{clean_title}"
created_at: {now_str}
tags:
  - war-room
  - pre-mortem
  - red-team
  - decision-strategy
  - risk-mitigation
links:
  - "[[index]]"
  - "[[RULES]]"
---

# War Room Pre-Mortem: {clean_title}

> **Simulasi Red Team Adversary & Stress-Testing Keputusan**  
> Dihasilkan secara otonom melalui **PROTOKOL 6: OPERASI WAR ROOM PRE-MORTEM**  
> Tanggal Analisis: `{now_str}`

---

## 1. Tesis Retrospektif (Kilas Balik Kegagalan dari Masa Depan)

{data.get('executive_premortem_thesis', '')}

---

## 2. Failure Modes (3 Skenario Kegagalan Paling Realistis)

{failure_rows}

## 3. Unstated Assumptions (Asumsi Terselubung vs Fakta Lapangan)

| No | Asumsi Terselubung | Mengapa Rapuh / Cacat | Reality Check & Batasan Riil |
| :--- | :--- | :--- | :--- |
{assump_rows}

---

## 4. Blindspot Questions (5 Pertanyaan Tajam yang Wajib Dijawab)

{questions_rows}

---

## 5. Actionable Mitigation & Circuit Breaker Protocol

{mitig_rows}

## 6. Grounding Vault & Audit Traceability

### A. Titik Stres & Bias Kognitif Masa Lalu (`journal/`)
{journal_links}

### B. Sounding Board & Jaringan Pakar Terkait (`crm/`)
{crm_links}

### C. Referensi Teknis & Batasan Arsitektur (`wiki/` & `lattices/`)
{tech_links}
"""
    return md, slug


def update_indexes(target_filename: str, title: str):
    """Reconciles index.md and INDEX.md with the newly created War Room document."""
    slug = Path(target_filename).stem
    new_entry = f"| [[in_motion/{slug}|{title}]] | `war_room` | 3 | 0 |\n"

    # Update index.md
    index_path = REPO_ROOT / "index.md"
    if index_path.exists():
        content = index_path.read_text(encoding="utf-8")
        if slug not in content:
            marker = "## 1. Active Workstreams (`in_motion/`)\n\n### Core Work (Professional & Enterprise Deliverables)\n| Deliverable | Status | Outgoing | Backlinks |\n| :--- | :--- | :--- | :--- |\n"
            if marker in content:
                content = content.replace(marker, marker + new_entry)
                index_path.write_text(content, encoding="utf-8")
                print(f"[*] Reconciled index.md with [[in_motion/{slug}]]")

    # Update INDEX.md
    index_caps = REPO_ROOT / "INDEX.md"
    if index_caps.exists():
        content = index_caps.read_text(encoding="utf-8")
        if slug not in content:
            if "## 1. Active Workstreams" in content:
                content = re.sub(
                    r"(## 1\. Active Workstreams.*?\|\s*:---\s*\|\s*:---\s*\|\s*:---\s*\|\s*:---\s*\|\n)",
                    r"\1" + new_entry,
                    content,
                    flags=re.DOTALL
                )
                index_caps.write_text(content, encoding="utf-8")
                print(f"[*] Reconciled INDEX.md with [[in_motion/{slug}]]")


def log_operation(slug: str, decision: str):
    """Appends WAR_ROOM operation to log.md in table format."""
    log_path = REPO_ROOT / "log.md"
    if not log_path.exists():
        return
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    entry = f"| {now_str} | WAR_ROOM | `in_motion/{slug}.md` | War Room Pre-Mortem stress-test: {decision} via PROTOKOL 6 |\n"
    try:
        content = log_path.read_text(encoding="utf-8")
        if not content.endswith("\n"):
            content += "\n"
        log_path.write_text(content + entry, encoding="utf-8")
        print(f"[*] Audit trail recorded in log.md: WAR_ROOM [[in_motion/{slug}]]")
    except Exception as e:
        print(f"[!] Failed to update log.md: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="Red Team Adversary & Decision Pre-Mortem Engine (PROTOKOL 6: OPERASI WAR ROOM)"
    )
    parser.add_argument("decision", nargs="*", default=[], help="Keputusan atau rencana yang ingin diuji (e.g. Rencana migrasi pipeline data)")
    parser.add_argument("--decision", dest="opt_decision", help="Explicit decision argument")
    parser.add_argument("--dry-run", action="store_true", help="Preview analysis without writing files")

    args = parser.parse_args()
    decision_text = args.opt_decision or " ".join(args.decision).strip()

    if not decision_text:
        decision_text = "Rencana Migrasi Pipeline Data (Streaming Feature Store & Hybrid Scoring Architecture)"
        print(f"[*] No explicit decision passed. Defaulting to high-stakes vault initiative:")
        print(f"    '{decision_text}'")

    print(f"[*] Initiating WAR ROOM PRE-MORTEM for:")
    print(f"    Target: \"{decision_text}\"")

    # 1. Gather traces
    print("[*] Gathering past stressors from journal/...")
    journals = scan_journal_biases()

    print("[*] Mapping network sounding boards from crm/...")
    crms = scan_crm_contacts()

    print("[*] Extracting technical & architectural assumptions from wiki/ and lattices/...")
    tech_notes = scan_technical_assumptions(decision_text)

    # 2. Call Red Team AI Engine
    print("[*] Engaging Red Team Adversary Engine...")
    data = call_gemini_war_room(decision_text, journals, crms, tech_notes)
    if not data:
        print("[*] AI cascade offline or unavailable. Engaging deterministic Red Team strategist...")
        data = generate_heuristic_war_room(decision_text, journals, crms)

    # 3. Format markdown
    md_content, slug = format_war_room_markdown(decision_text, data, journals, crms, tech_notes)
    target_filename = f"war_room_{slug}.md"
    target_file = REPO_ROOT / "in_motion" / target_filename

    if args.dry_run:
        print(f"\n[DRY RUN PREVIEW] Output path: in_motion/{target_filename}\n")
        print(md_content[:1500])
        print("\n... (truncated for preview) ...")
        return

    # Write file
    target_file.parent.mkdir(parents=True, exist_ok=True)
    target_file.write_text(md_content, encoding="utf-8")
    print(f"[+] Created War Room Pre-Mortem report: in_motion/{target_filename}")

    # 4. Reconcile Indexes
    update_indexes(target_filename, f"War Room Pre-Mortem: {data.get('project_title', decision_text)}")

    # 5. Log Operation
    log_operation(target_file.stem, decision_text)

    # 6. Re-index search engine
    try:
        sys.path.insert(0, str(REPO_ROOT / "tools"))
        import indexer
        indexer.build_index(verbose=False)
        print("[*] Hybrid search index updated successfully.")
    except Exception as e:
        print(f"[!] Warning: Index update skipped: {e}")

    print(f"\n[SUCCESS] WAR ROOM PRE-MORTEM completed successfully.")
    print(f"File created: in_motion/{target_filename}")

    # Visual Executive Summary directly in terminal
    title = data.get("project_title", decision_text)
    print("\n" + "=" * 78)
    print(f"💀 WAR ROOM PRE-MORTEM EXECUTIVE SUMMARY: {title}")
    print("=" * 78)
    print(f"\n[!] RETROSPEKTIF KEGAGALAN DARI MASA DEPAN:\n{data.get('executive_premortem_thesis', '')}\n")
    
    print("[-] 3 SKENARIO KEGAGALAN PALING REALISTIS:")
    for idx, fm in enumerate(data.get("failure_modes", []), 1):
        print(f"  {idx}. {fm['scenario']} (Probabilitas: {fm.get('probability', 'Tinggi')})")
        print(f"     Leading Indicator: {fm['trigger_event']}")
        
    print("\n[?] 5 PERTANYAAN BLINDSPOT WAJIB DIJAWAB SEBELUM COMMIT:")
    for idx, q in enumerate(data.get("blindspot_questions", []), 1):
        print(f"  {idx}. {q}")
        
    print("\n[#] ACTIONABLE MITIGATION & KILL-SWITCH THRESHOLDS:")
    for idx, am in enumerate(data.get("actionable_mitigations", []), 1):
        print(f"  {idx}. {am['action']}")
        print(f"     Batas Toleransi (Kill-Switch): {am['metric_threshold']}")
        
    print("=" * 78)
    print(f"📖 Baca dokumen lengkap di terminal : cat in_motion/{target_filename}")
    print(f"📱 Atau baca di Telegram bot        : /read {target_file.stem}")
    print("=" * 78 + "\n")


if __name__ == "__main__":
    main()
