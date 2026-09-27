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

## 2. Enam Protokol Operasi Otonom Agen


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

1. **Penelusuran Konteks (Grounded Hybrid Search)**:
   - **WAJIB**: Agen terlebih dahulu menjalankan skrip pencarian hybrid lokal untuk mengumpulkan konteks sebelum menyusun jawaban:
     ```bash
     python tools/search.py "<pertanyaan_atau_kata_kunci>" --top-k 5
     ```
     *(Gunakan opsi `--json` jika agen memerlukan keluaran terstruktur untuk reasoning engine)*.
   - Skrip ini menggabungkan pencarian exact keyword BM25 dan dense semantic vector search untuk mengidentifikasi potongan teks (*chunks*) paling relevan lengkap dengan nomor baris spesifik (`#L...`) dan judul section.
   - Jika terdapat file baru yang belum terindeks atau database indeks belum tersedia, jalankan:
     ```bash
     python tools/indexer.py
     ```
   - Periksa juga [index.md](file:///C:/Users/tio/.gemini/antigravity/scratch/second-brain/index.md) untuk melihat peta konektivitas jaringan dan *backlink matrix*.

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

### PROTOKOL 5: OPERASI WEAVE (Sintesis & Analogi Struktural Lintas Domain)

Setiap kali pengguna meminta untuk menjalankan operasi `WEAVE` atau menghubungkan dua bidang/domain yang tampak tidak berhubungan:

**Format Perintah Pengguna**:
> *"Jalankan operasi WEAVE antara domain [Domain A] dan [Domain B]"*  
> *(Contoh: "Jalankan operasi WEAVE antara domain Credit Risk/Data Architecture dan Tactical Football Analytics / Behavioral Economics")*

**Instruksi Pelaksanaan Wajib bagi Agen**:

1. **Penelusuran Konsep Multi-Domain**:
   - Telusuri konsep-konsep di `wiki/`, `in_motion/`, dan `lattices/` yang merepresentasikan Domain A dan Domain B.
   - Jalankan `python tools/search.py "<Domain A>"` dan `python tools/search.py "<Domain B>"` untuk mengekstrak grounding konteks dan potongan teks spesifik dari kedua domain.
2. **Identifikasi Abstraksi Isomorfik (Tingkat Tinggi)**:
   - Temukan pola *first-principles* atau analogi struktural yang mendasari kedua domain, seperti:
     - *Feedback loops & delayed consequence* (umpan balik sistemik).
     - *Bottlenecks & Theory of Constraints* (hambatan kapasitas aliran).
     - *Probability shifting & Fat-tailed asymmetric risk* (pergeseran probabilitas ekstrim).
     - *Fragility vs Antifragility* (daya tahan sistem saat menerima tekanan).
     - *Exploration vs Exploitation trade-offs* (eksplorasi peluang vs eksploitasi hasil).
     - *Spatial-temporal coordination & dynamic role shifting* (koordinasi ruang-waktu adaptif).
3. **Penyusunan Catatan Sintesis Baru (`wiki/synthesis_[TopikA]_[TopikB].md`)**:
   - Buat file baru dengan konvensi nama: `wiki/synthesis_[TopikA]_[TopikB].md` (format clean slug).
   - Terapkan skema YAML Frontmatter terstandarisasi:
     ```yaml
     ---
     title: "Sintesis Lintas Domain: [Topik A] x [Topik B]"
     type: cross_domain_synthesis
     domain_a: "[Domain A]"
     domain_b: "[Domain B]"
     created_at: YYYY-MM-DD
     tags:
       - weave
       - cross-domain
       - structural-analogy
       - mental-model
     links:
       - "[[konsep-terkait-domain-a]]"
       - "[[konsep-terkait-domain-b]]"
     ---
     ```
   - Susun isi dokumen dengan struktur baku 4 seksi:
     - **1. Tesis & Analogi Struktural Tingkat Tinggi**: Penjelasan isomorfisma konseptual yang menghubungkan kedua domain secara sistemik.
     - **2. Matriks Pemetaan Isomorfik**: Tabel komparasi domain (Dimensi Sistem | Domain A | Domain B | Abstraksi Bersama).
     - **3. Tiga Transfer Ilmu Konkret (Cross-Pollination)**: Jelaskan secara presisi dan teknis bagaimana solusi, metodologi, atau algoritma dari Domain B dapat memecahkan masalah umum di Domain A:
       - *Transfer 1*: Solusi taktis B untuk masalah kronis di A.
       - *Transfer 2*: Kerangka evaluasi B untuk mitigasi blindspot di A.
       - *Transfer 3*: Mekanisme adaptasi B untuk optimasi performa di A.
     - **4. Implikasi Eksekusi & Next Action**: Rekomendasi playbook atau eksperimen konkret di `in_motion/`.
4. **Rekonsiliasi Indeks & Konektivitas Graf**:
   - Daftarkan file sintesis baru ini ke kedua klaster konsep di [index.md](file:///C:/Users/tio/.gemini/antigravity/scratch/second-brain/index.md) dan [INDEX.md](file:///C:/Users/tio/.gemini/antigravity/scratch/second-brain/INDEX.md).
   - Jalankan `python tools/indexer.py` agar dokumen sintesis baru langsung terindeks di mesin pencarian hybrid SQLite.
5. **Pencatatan Audit Trail**:
   - Catat operasi ke dalam [log.md](file:///C:/Users/tio/.gemini/antigravity/scratch/second-brain/log.md) dengan tipe `WEAVE`.

---

### PROTOKOL 6: OPERASI WAR ROOM PRE-MORTEM (Red Team Adversary & Stress-Testing Keputusan)

Setiap kali pengguna meminta untuk menjalankan simulasi War Room, Pre-Mortem, atau Red Teaming terhadap rencana/keputusan kritis:

**Format Perintah Pengguna**:
> *"Role: Red Team Adversary & Decision Strategist. Jalankan simulasi War Room Pre-Mortem untuk [Nama Keputusan / Proyek]"*  
> *(Contoh: "Jalankan simulasi War Room Pre-Mortem untuk Rencana migrasi pipeline data / Pengambilan proyek konsultasi baru / Strategi negosiasi dengan partner X")*

**Instruksi Pelaksanaan Wajib bagi Agen**:

1. **Triangulasi Konteks & Audit Jejak Historis**:
   - Telusuri `journal/` untuk mendeteksi pola bias kognitif masa lalu (*builder's over-optimism*, *cognitive overflow*, *delayed feedback*, atau friksi operasional yang pernah menimbulkan stres tinggi).
   - Telusuri `crm/` untuk mengecek apakah ada individu dalam jaringan pengguna yang memiliki keahlian relevan, sudut pandang berlawanan (*devil's advocate*), atau dapat dijadikan *sounding board* kritis.
   - Telusuri `wiki/` dan `lattices/` (termasuk arsitektur sistem dan SLA latensi) untuk menguji keabsahan asumsi teknis serta menemukan titik kerapuhan (*fragility points*).
2. **Simulasi Retrospektif dari Masa Depan (Pre-Mortem Mindset)**:
   - Asumsikan skenario terburuk: Kita berada di 6–12 bulan ke depan, dan inisiatif ini telah **gagal total** secara memalukan, membakar anggaran, dan mengacaukan operasional.
   - Bedah mekanisme kegagalan tanpa kompromi (*zero-sugarcoating*).
3. **Penyusunan Laporan War Room (`in_motion/war_room_[nama_proyek].md`)**:
   - Buat file baru di direktori `in_motion/` dengan skema Frontmatter:
     ```yaml
     ---
     title: "War Room Pre-Mortem: [Nama Proyek]"
     type: war_room_pre_mortem
     status: active
     decision_target: "[Nama Proyek / Keputusan]"
     created_at: YYYY-MM-DD
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
     ```
   - Susun isi dokumen dengan struktur 5 seksi baku:
     - **1. Tesis Retrospektif (Kilas Balik Kegagalan)**: Penjelasan naratif mengapa rencana ini runtuh dari sudut pandang masa depan.
     - **2. Failure Modes (Pre-Mortem)**: 3 skenario kegagalan paling realistis beserta probabilitas, rantai kausalitas teknis/psikologis, dan *leading indicator* (tanda bahaya awal).
     - **3. Unstated Assumptions**: Tabel komparasi (Asumsi Terselubung | Mengapa Rapuh/Cacat | Reality Check & Batasan Riil).
     - **4. Blindspot Questions**: 5 pertanyaan tajam tanpa kompromi yang wajib dijawab sebelum berkomitmen mengalokasikan waktu/modal.
     - **5. Actionable Mitigation & Circuit Breakers**: Protokol mitigasi preventif dengan ambang batas kuantitatif tegas (*kill-switch threshold*).
     - **6. Grounding Vault & Audit Traceability**: Tautan balik ke catatan `journal/`, kontak `crm/`, dan dokumen `wiki/` terkait.
4. **Rekonsiliasi Indeks & Mesin Pencarian**:
   - Daftarkan dokumen baru ke [`index.md`](file:///C:/Users/tio/.gemini/antigravity/scratch/second-brain/index.md) dan [`INDEX.md`](file:///C:/Users/tio/.gemini/antigravity/scratch/second-brain/INDEX.md) di bagian *Active Workstreams*.
   - Jalankan `python tools/indexer.py` agar laporan langsung terindeks di mesin pencarian hybrid.
5. **Pencatatan Audit Trail**:
   - Catat operasi ke dalam [`log.md`](file:///C:/Users/tio/.gemini/antigravity/scratch/second-brain/log.md) dengan tipe `WAR_ROOM`.

---

## 3. Standar Kualitas Keluaran & Etika Kognitif


1. **Non-Asumsi & Evidence-First**: Jangan mengarang data atau entitas baru tanpa dasar teks yang jelas dari sumber `raw/` atau interaksi pengguna.
2. **Zero Dangling Orphans Tanpa Alasan**: Setiap file baru di `wiki/`, `journal/`, atau `crm/` wajib terhubung minimal ke 1 nodus lain dan tercatat di indeks masing-masing.
3. **Preservasi Konten Mentah**: File asli di `raw/` tidak boleh dihapus secara permanen; selalu pindahkan ke `raw/processed/` agar riwayat provenance terjaga utuh.
