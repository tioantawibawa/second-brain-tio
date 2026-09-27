# System Rules & Knowledge Architecture Governance

Dokumen ini mendefinisikan arsitektur kognitif, aturan penamaan, skema linking, dan standar visual untuk repository Second Brain ini. Repository ini **bukan template PARA generik**, melainkan sistem **momentum-driven** yang dirancang untuk profil *deliverable-first*, konkurensi multi-lini (kerja & side-project builder), dan orientasi eksekusi tinggi (*ideas pushed to deployment*).

---

## 1. Topologi Kognitif (Non-PARA Architecture)

Struktur folder dibatasi maksimal 2 tingkat kedalaman untuk mencegah *cognitive friction* dan *folder burying*:

```
second-brain/
├── inbox_raw/             # Level 1: Buffer dump mentah, transkrip, voice memo (append-only)
├── in_motion/             # Level 1: Ide dan proyek dalam eksekusi aktif
│   ├── core_work/         # Level 2: Pekerjaan profesional, enterprise deliverables, klien
│   └── side_builder/      # Level 2: Eksperimen, arsitektur AI agent, prototipe builder
├── lattices/              # Level 1: Jaringan sintesis & scaffold pengetahuan permanen
│   ├── mental_models/     # Level 2: Arsitektur sistem, hukum kognitif, kerangka analitis
│   └── playbooks/         # Level 2: SOP teknis teruji, pattern engineering, template arsitektur
├── system_triggers/       # Level 1: Pemicu aksi, automasi, & engine eksekusi
│   ├── templates/         # Level 2: Template Markdown standar berstruktur rapi
│   └── cadences/          # Level 2: Checklist pulse harian/mingguan & deployment triggers
└── scripts/               # Level 1: Otomasi ingest, parsing AI, dan semantic indexing
```

---

## 2. Naming Conventions

1. **Format File**:
   - Selalu gunakan `kebab-case.md` huruf kecil tanpa spasi (misal: `autonomous-agent-evals.md`).
   - Untuk log harian atau trigger bertanggal, gunakan awalan ISO `YYYYMMDD-kebab-case.md` (misal: `20260927-daily-pulse.md`).
2. **Karakter Terlarang**:
   - Hindari karakter khusus di nama file: `?`, `:`, `\`, `/`, `*`, `"`, `<`, `>`, `|`.

---

## 3. Frontmatter Schema (YAML)

Setiap catatan yang diproses wajib memiliki YAML frontmatter di bagian paling atas:

```yaml
---
title: "Autonomous Agent Evaluation Framework"
id: "20260927-autonomous-agent-evals"
type: in_motion | lattice | trigger
stream: core_work | side_builder | meta_system
status: seed | incubating | active | deployed | evergreen
created_at: 2026-09-27
updated_at: 2026-09-27
tags:
  - ai-agents
  - evaluation
  - production
links:
  - "[[latency-optimization-playbook]]"
  - "[[eval-harness-v1]]"
---
```

### Definisi Status:
- `seed`: Ide mentah yang baru dipilah dari inbox.
- `incubating`: Sedang dalam riset atau perancangan arsitektur.
- `active`: Sedang dikerjakan dalam sprint saat ini (*in motion*).
- `deployed`: Deliverable telah dirilis / kode telah hidup di production.
- `evergreen`: Pengetahuan fundamental atau model mental yang berlaku terus-menerus (*lattice*).

---

## 4. Wikilinking & Knowledge Graph

1. **Syntax**:
   - Gunakan format Obsidian / GFM standard: `[[target-note-slug]]` atau `[[target-note-slug|Display Alias]]`.
2. **Atomic & Scaffolded**:
   - Setiap catatan `in_motion` harus merujuk ke minimal satu `lattice` (landasan arsitektur/mental model).
   - Tautan ke ide yang belum dibuat (*dangling link*, misal `[[unbuilt-feature]]`) **sangat dianjurkan** sebagai pemicu ide builder berikutnya.
3. **Kompatibilitas Tools**:
   - Berfungsi 100% di **Obsidian** (Graph View, Dataview plugin, Backlinks tab).
   - Berfungsi 100% di **Neovim** (`obsidian.nvim`, `telekasten.nvim`, `telescope`).

---

## 5. Visual & Output Standard

Sesuai standar kognitif pengguna (*statistically grounded, executive-ready, rapi visual*):
1. **Deliverable-First**: Setiap catatan `in_motion` harus diawali dengan **Target Output** yang jelas dan terukur, bukan narasi abstrak.
2. **Tabel & Diagram**:
   - Gunakan tabel Markdown untuk data perbandingan atau metrik performa.
   - Gunakan Mermaid (` ```mermaid `) untuk arsitektur sistem, aliran data, atau state machine.
3. **Execution Checklist**:
   - Gunakan task syntax: `- [ ] Deliverable item` untuk memudahkan pemantauan progres.
