# Autonomous Agent Operational Manual (`agents.md`)

> **MANUAL OPERASIONAL OTONOM UNTUK AI AGENT & PAIR-PROGRAMMER**
> Dokumen ini adalah acuan hukum operasional tertinggi yang **WAJIB dibaca dan dipatuhi** oleh AI agent setiap kali berinteraksi, memproses data, menjawab pertanyaan, atau memperbarui repository Second Brain ini.

---

## 1. Arsitektur Folder & Topologi Vault

```
second-brain/
├── agents.md              # Dokumen ini: Manual protokol operasional otonom agen
├── index.md               # Katalog utama seluruh konsep & entitas di wiki/
├── log.md                 # Audit log kronologis seluruh tindakan ingest, query, & update
├── raw/                   # Kliping web, transkrip video/YouTube, catatan meeting mentah
│   └── processed/         # Arsip sumber setelah selesai diekstraksi ke wiki/
├── wiki/                  # Halaman atomik: konsep, entitas, alat, sintesis topik, ide
├── journal/               # Refleksi harian & catatan strategi berkala
│   └── index.md           # Indeks kronologis jurnal (Tanggal | Judul | Ringkasan 1 Kalimat)
├── crm/                   # Profil individu, kolaborator, rekan bisnis, klien
│   └── index.md           # Direktori alfabetis kontak, bio singkat, & topik terkait
├── inbox_raw/             # Buffer dump cepat & voice note Telegram
├── in_motion/             # Workstream & deliverable aktif (core_work & side_builder)
├── lattices/              # Scaffold pengetahuan permanen (mental_models & playbooks)
└── system_triggers/       # Template Markdown & checklist cadence mingguan
```

---

## 2. Empat Protokol Operasi Otonom Agen

### PROTOKOL 1: OPERASI INGEST (`raw/` $\rightarrow$ `wiki/`)

Setiap kali agen diperintahkan untuk melakukan ingest atau mendeteksi file baru di `raw/`:

1. **Pemindaian**:
   - Baca setiap file Markdown/teks di direktori `raw/`.
   - **Abaikan** file yang berada di dalam subfolder `raw/processed/`.
2. **Ekstraksi Cerdas**:
   - Identifikasi dan ekstrak:
     - **Ide Inti & Tesis Utama** (*Core Insight*).
     - **Entitas Kunci & Tokoh**: Orang atau institusi penting (hubungkan ke `crm/` jika relevan).
     - **Tools, Library, atau Arsitektur**: Perkakas teknis yang dapat digunakan kembali.
     - **Action Items / Implikasi Praktis**: Checklist tindak lanjut.
3. **Penyusunan Halaman `wiki/`**:
   - Buat file baru atau perbarui halaman yang sudah ada di `wiki/[nama-topik].md`.
   - Gunakan format penamaan `kebab-case.md`.
   - Gunakan tautan dua arah (*bidirectional wikilinks*) `[[...]]` yang merujuk balik ke file sumber aslinya di `[[raw/processed/...]]`.
4. **Skema Metadata YAML Frontmatter (Wajib)**:
   ```yaml
   ---
   title: "Judul Konsep atau Sintesis"
   source_title: "Judul Asli Sumber / Artikel / Video"
   source_url: "https://..."
   author: "Nama Channel / Penulis / Pembicara"
   ingest_date: YYYY-MM-DD
   tags:
     - wiki
     - topic-tag
   links:
     - "[[related-wiki-concept]]"
     - "[[raw/processed/source-file]]"
   ---
   ```
5. **Pembaruan Indeks & Audit Log**:
   - Tambahkan entri topik baru ke dalam [index.md](file:///C:/Users/tio/.gemini/antigravity/scratch/second-brain/index.md).
   - Tambahkan baris audit log baru di [log.md](file:///C:/Users/tio/.gemini/antigravity/scratch/second-brain/log.md) dengan tipe `INGEST`.
6. **Pengarsipan File Sumber**:
   - Pindahkan file sumber dari `raw/[nama-file]` ke `raw/processed/[nama-file]`.

---

### PROTOKOL 2: OPERASI QUERY (Compounding Knowledge)

Setiap kali pengguna mengajukan pertanyaan analitis, konsultasi arsitektur, atau sintesis gagasan:

1. **Penelusuran Konteks (Grounding)**:
   - Periksa [index.md](file:///C:/Users/tio/.gemini/antigravity/scratch/second-brain/index.md) dan cari referensi konsep terkait di dalam direktori `wiki/`, `in_motion/`, dan `lattices/`.
   - Gunakan skrip pencarian lokal `python scripts/graph_index.py search "<query>"` untuk menemukan konteks yang paling relevan secara matematis (BM25).
2. **Formulasi Jawaban Ter-Grounding**:
   - Berikan jawaban yang bersandar kuat (*grounded*) pada catatan yang tersimpan di dalam vault.
   - Cantumkan referensi wikilinks `[[nama-catatan]]` pada setiap klaim atau pola yang dirujuk.
3. **Sintesis Baru (Compounding)**:
   - **Evaluasi**: Apakah respon analitis yang diberikan menghasilkan prinsip, kerangka kerja, atau sintesis baru yang belum terdokumentasi dan bernilai pakai ulang (*reusable*)?
   - **Jika YA, agen WAJIB bertindak otonom**:
     1. Buat halaman baru di `wiki/[topik-baru].md`.
     2. Tambahkan frontmatter lengkap dan tautkan timbal-balik ke konsep pendukungnya.
     3. Daftarkan topik baru tersebut di [index.md](file:///C:/Users/tio/.gemini/antigravity/scratch/second-brain/index.md).
     4. Catat tindakan compounding ini di [log.md](file:///C:/Users/tio/.gemini/antigravity/scratch/second-brain/log.md) dengan tipe `QUERY_COMPOUND`.

---

### PROTOKOL 3: OPERASI JOURNAL (Refleksi & Pola Kognitif)

Setiap kali pengguna menulis atau mendiktekan jurnal refleksi, status harian, atau retrospeksi:

1. **Konvensi Penamaan File**:
   - Format wajib: `journal/YYYY-MM-DD_[judul-singkat].md` (contoh: `journal/2026-09-28_refleksi-arsitektur-agen.md`).
2. **Skema Metadata**:
   ```yaml
   ---
   title: "Judul Singkat Jurnal"
   date: YYYY-MM-DD
   type: journal
   tags:
     - reflection
     - daily-pulse
   links:
     - "[[relevant-wiki-topic]]"
   ---
   ```
3. **Pembaruan Indeks Jurnal**:
   - Buka [journal/index.md](file:///C:/Users/tio/.gemini/antigravity/scratch/second-brain/journal/index.md).
   - Tambahkan baris baru di tabel: `| YYYY-MM-DD | [[YYYY-MM-DD_judul-singkat\|Judul Singkat]] | Ringkasan padat 1 kalimat |`.
4. **Pola Respons AI**:
   - Saat merespon atau mendiskusikan jurnal pengguna, agen **wajib mensintesis 3 lensa**:
     1. Konsep pengetahuan di `wiki/` (landasan teknis/prinsip).
     2. Pola historis dari entri `journal/` masa lalu (menemukan bias, siklus energi, atau hambatan berulang).
     3. Catatan relasi di `crm/` (jika jurnal menyinggung interaksi dengan kolega/klien).
5. **Audit Log**:
   - Catat operasi pembuatan jurnal di [log.md](file:///C:/Users/tio/.gemini/antigravity/scratch/second-brain/log.md) dengan tipe `JOURNAL`.

---

### PROTOKOL 4: OPERASI CRM (Manajemen Jaringan & Profil Individu)

Setiap kali ada tokoh, kolaborator, investor, mentor, klien, atau rekan diskusi baru yang muncul di dalam catatan atau transkrip:

1. **Konvensi Penamaan File**:
   - Format wajib: `crm/[Nama-Lengkap].md` (contoh: `crm/Tiago-Forte.md`, `crm/Budi-Santoso.md`).
2. **Skema Halaman Profil CRM**:
   ```yaml
   ---
   name: "Nama Lengkap"
   role: "Jabatan / Bidang Keahlian / Posisi"
   organization: "Perusahaan / Komunitas / Afiliasi"
   interaction_last_date: YYYY-MM-DD
   tags:
     - crm
     - collaborator | client | expert
   links:
     - "[[wiki-topic-of-expertise]]"
   ---

   # Nama Lengkap

   ## 1. Bio Singkat & Konteks Relasi
   Deskripsi padat mengenai siapa individu ini dan bagaimana hubungan kerjanya dengan pengguna.

   ## 2. Topik & Proyek Terkait (`wiki/` & `in_motion/`)
   - `[[topik-keahlian]]`
   - `[[proyek-kolaborasi]]`

   ## 3. Log Interaksi & Keputusan Penting
   - **YYYY-MM-DD**: Ringkasan poin penting dari diskusi atau transkrip meeting.
   ```
3. **Pembaruan Indeks CRM**:
   - Buka [crm/index.md](file:///C:/Users/tio/.gemini/antigravity/scratch/second-brain/crm/index.md).
   - Masukkan nama individu sesuai **urutan alfabetis (A-Z)** beserta tautan profil, bio singkat, dan wikilink ke topik terkait di `wiki/`.
4. **Audit Log**:
   - Catat operasi CRM di [log.md](file:///C:/Users/tio/.gemini/antigravity/scratch/second-brain/log.md) dengan tipe `CRM`.

---

## 3. Standar Kualitas Keluaran & Etika Kognitif

1. **Non-Asumsi & Evidence-First**: Jangan mengarang data atau entitas baru tanpa dasar teks yang jelas dari sumber `raw/` atau interaksi pengguna.
2. **Zero Dangling Orphans Tanpa Alasan**: Setiap file baru di `wiki/`, `journal/`, atau `crm/` wajib terhubung minimal ke 1 nodus lain dan tercatat di indeks masing-masing.
3. **Preservasi Konten Mentah**: File asli di `raw/` tidak boleh dihapus secara permanen; selalu pindahkan ke `raw/processed/` agar riwayat provenance terjaga utuh.
