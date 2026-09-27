---
title: "Mengatasi Kelupaan Komitmen Proyek dari Rapat"
date: 2026-09-27
type: journal
tags:
  - reflection
  - daily-pulse
  - meetings
  - cognitive-load
  - project-tracking
links:
  - "[[journal/index]]"
  - "[[identity-debugging-walk-protocol]]"
  - "[[weekly-pulse]]"
  - "[[tmpl_in_motion]]"
  - "[[RULES]]"
---

# Mengatasi Kelupaan Komitmen Proyek dari Rapat

## 1. Entri Refleksi Asli Pengguna
> *"Saya suka lupa project-project yang disampaikan ke rapat."*

---

## 2. Analisis Kognitif & Diagnosa Akar Masalah

Berdasarkan profil kognitif pengguna (*high-concurrency builder* dengan banyak lini paralel yang berjalan bersamaan):

1. **Cognitive Overflow akibat Konkurensi Tinggi**:
   Saat rapat berlangsung, otak aktif memproses diskusi sambil secara simultan memikirkan implementasi teknis (*builder mode*). Informasi baru yang hanya disimpan di *working memory* (RAM mental) akan langsung terhapus ketika fokus berpindah ke masalah teknis berikutnya.
2. **Ketiadaan Triage Zero-Friction Pasca Rapat**:
   Sebagian besar catatan rapat hilang bukan karena tidak dicatat, tetapi karena dicatat di media acak (kertas coretan, tab browser, aplikasi notes bawaan) tanpa jalur masuk langsung ke sistem kerja nyata.
3. **Pelanggaran Prinsip *"Stored in Motion"***:
   Sesuai doktrin di [`[[identity-debugging-walk-protocol]]`](file:///C:/Users/tio/.gemini/antigravity/scratch/second-brain/lattices/mental_models/identity-debugging-walk-protocol.md), sebuah ide atau proyek yang disimpan secara pasif tanpa metrik keluaran langsung akan mati (*"stored statically, it dies"*).

---

## 3. Rekomendasi Taktis Berdasarkan 3 Lensa Knowledge OS

### A. Lensa `wiki/` & `lattices/` (Sistemik & Arsitektural)
1. **Protokol 60 Detik Pasca Rapat (Telegram Voice Dump)**:
   - Tepat setelah rapat selesai, buka chat Telegram bot Second Brain Anda.
   - Rekam Voice Note selama 30–60 detik dengan formula:
     > *"Rapat tadi dengan [Nama PIC], keputusannya kita harus deploy [Nama Proyek / Fitur] dengan deadline [Tanggal]. Langkah pertamanya adalah [Action Item 1]."*
   - Bot otomatis memproses audio via Gemini 3.8 Flash, membuat file di [`in_motion/core_work/`](file:///C:/Users/tio/.gemini/antigravity/scratch/second-brain/in_motion/core_work), dan mengekstrak checklist `- [ ]`.
2. **Gunakan Template Deliverable-First**:
   - Jika membuat catatan manual, gunakan template [`[[tmpl_in_motion]]`](file:///C:/Users/tio/.gemini/antigravity/scratch/second-brain/system_triggers/templates/tmpl_in_motion.md). Jangan mencatat notula rapat yang panjang; catat hanya **Target Deliverable**, **Target Date**, dan **Checklist Eksekusi**.
3. **Review Cadence Mingguan**:
   - Setiap akhir pekan, jalankan protokol [`[[weekly-pulse]]`](file:///C:/Users/tio/.gemini/antigravity/scratch/second-brain/system_triggers/cadences/weekly-pulse.md) Bagian 2 (*Review Lini Konkuren*) untuk menginspeksi folder `in_motion/core_work/` agar tidak ada komitmen proyek yang tertinggal.

### B. Lensa `journal/` (Pola Perilaku & Hambatan Berulang)
- Pola historis menunjukkan bahwa energi Anda melonjak pada fase perancangan arsitektur dan coding (*side_builder*), namun rawan mengalami friksi pada pelacakan administrasi meeting.
- **Intervensi**: Jadikan pencatatan proyek rapat sebagai "transaksi satu tombol" (cukup kirim pesan singkat atau VN ke bot Telegram di smartphone saat berjalan keluar dari ruang rapat).

### C. Lensa `crm/` (Akuntabilitas Pemangku Kepentingan)
- Setiap proyek yang disepakati di rapat harus memiliki minimal satu nama individu pemilik di [`crm/index.md`](file:///C:/Users/tio/.gemini/antigravity/scratch/second-brain/crm/index.md).
- Buat file kontak baru di `crm/[Nama-Rekan].md` jika ada PIC atau klien baru, dan kaitkan proyek tersebut ke profilnya. Proyek yang memiliki wajah orang yang nyata jauh lebih sulit dilupakan daripada ide abstrak.

---

## 4. Checklist Aksi Preventif Segera
- [ ] Buat Voice Note dump di Telegram untuk proyek-proyek rapat yang masih diingat hari ini.
- [ ] Buka `in_motion/core_work/` dan pastikan setiap deliverable rapat terdaftar sebagai catatan aktif.
- [ ] Evaluasi komitmen rapat tersebut pada sesi [`[[weekly-pulse]]`](file:///C:/Users/tio/.gemini/antigravity/scratch/second-brain/system_triggers/cadences/weekly-pulse.md) berikutnya.
