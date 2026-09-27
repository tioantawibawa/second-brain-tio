# Second Brain: Momentum & Deliverable-Driven Knowledge OS

> **Customized Knowledge Architecture for High-Concurrency Builders & AI Engineers.**  
> Diselaraskan secara khusus untuk pola kerja *deliverable-first*, konkurensi tinggi (paralel kerja & side-project builder), visual rapi, dan orientasi eksekusi sampai tahap deployment.  
> 📖 **[Baca Panduan Lengkap Operasional (MANUAL.md)](file:///C:/Users/tio/.gemini/antigravity/scratch/second-brain/MANUAL.md)** untuk petunjuk detail seluruh fitur dari HP ke VPS.

---

## 1. Arsitektur Kognitif

Berbeda dengan model PARA tradisional yang pasif, sistem ini mengalirkan ide berdasarkan **momentum eksekusi**:

```mermaid
flowchart LR
    A["inbox_raw/ (Raw Capture)"] -->|ingest.py + Gemini| B{"Triage Engine"}
    B -->|Active Deliverable| C["in_motion/ (Execution)"]
    B -->|Synthesis / Architecture| D["lattices/ (Knowledge Scaffolds)"]
    C -.->|Triggers Tasks| E["system_triggers/ (Cadences & Automations)"]
    D -.->|Underpins| C
    C -->|Auto Indexer| F["INDEX.md (Network & Backlinks)"]
    D -->|Auto Indexer| F
```

| Direktori | Fungsi Utama | Karakteristik |
| :--- | :--- | :--- |
| `inbox_raw/` | Quick capture, voice notes, transkrip mentah, chat dump | Zero friction, append-only, dibersihkan setelah ingest |
| `in_motion/core_work/` | Deliverables profesional, proyek enterprise, target klien | Milestones terukur, SLA, deliverables-first |
| `in_motion/side_builder/` | Side-projects, eksperimen AI agents, riset SaaS | Cepat, iteratif, target: deploy atau live agent |
| `lattices/mental_models/` | Kerangka analitis, prinsip sistem, mental models | Abadi, sintetis, modular |
| `lattices/playbooks/` | Engineering SOP, checklist arsitektur, pattern teruji | Reusable blueprints & operational scripts |
| `system_triggers/` | Template markdown, cadences mingguan, automation scripts | Engine yang menjaga momentum tetap bergerak |

---

## 2. CLI Automation Suite

Repositori ini dilengkapi dengan utilitas CLI bawaan Python Standard Library (zero mandatory pip dependencies) yang terintegrasi dengan Google Gemini AI untuk analisis cerdas.

### A. Pipeline Ingest Catatan Mentah (`ingest.py`)
Memproses file teks di `inbox_raw/`, mengekstrak **Core Insight**, **Key Entities** (sebagai `[[wikilinks]]`), **Action Items/Triggers**, lalu menghasilkan catatan Markdown siap pakai.

```bash
# Memproses satu catatan tertentu
python scripts/ingest.py --file inbox_raw/draft-note.md

# Memproses seluruh isi folder inbox_raw secara otomatis
python scripts/ingest.py --all

# Mode dry-run (tampilkan hasil di terminal tanpa menulis file)
python scripts/ingest.py --file inbox_raw/draft-note.md --dry-run
```

*Tersedia juga helper script one-liner:*
- Linux/VPS: `./scripts/process_dump.sh`
- Windows: `.\scripts\process_dump.ps1`

### C. Telegram Ingest Gateway (`telegram_bot.py`)
Bot Telegram mandiri (Pure Python Standard Library, tanpa framework bot berat) yang memungkinkan Anda menangkap ide secara instan dari smartphone ke VPS:
- **Text Dump**: Kirim pesan teks mentah atau chat forward -> otomatis di-ingest & diklasifikasikan ke `in_motion/` atau `lattices/`.
- **Voice Note (VN) Dump**: Kirim rekaman suara (VN) langsung dari Telegram. Audio otomatis dikirim ke **Gemini 3.8 Flash Multimodal API** untuk ditranskripsikan secara presisi dan diubah menjadi dokumen Markdown berstandar eksekutif lengkap dengan *action triggers*.
- **Pencarian Cepat**: Ketik `/search <kata_kunci>` di chat Telegram untuk mencari catatan via algoritma BM25.
- **Statistik Vault**: Ketik `/status` untuk melihat ringkasan deliverable dan backlog.

```bash
# Menjalankan bot secara interaktif
python3 scripts/telegram_bot.py

# Atau jalankan sebagai systemd service di background (24/7)
sudo cp systemd/second-brain-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now second-brain-bot
```

---

## 3. Integrasi Obsidian & Neovim

### Obsidian
1. Buka Obsidian -> **Open folder as vault** -> pilih folder repositori ini.
2. Aktifkan fitur inti: **Graph View**, **Backlinks**, dan **Outgoing Links**.
3. Rekomendasi Community Plugins:
   - `Dataview`: Kueri status catatan otomatis berdasarkan YAML frontmatter.
   - `Omnisearch`: Pencarian teks mendalam.

### Neovim
1. Kompatibel dengan plugin Markdown modern:
   - `epwalsh/obsidian.nvim`
   - `renerocksai/telekasten.nvim`
   - `nvim-telescope/telescope.nvim`
2. Konfigurasi `obsidian.nvim` contoh:
   ```lua
   require("obsidian").setup({
     workspaces = {
       {
         name = "second-brain",
         path = "~/second-brain",
       },
     },
     wiki_link_func = "use_alias_only",
   })
   ```

---

## 4. Aturan & Governance

Lihat [RULES.md](file:///C:/Users/tio/.gemini/antigravity/scratch/second-brain/RULES.md) untuk detail lengkap mengenai skema frontmatter, konvensi penamaan file, dan standarisasi visual.
