---
title: "Weekly Pulse & Delivery Review Trigger"
id: "weekly-pulse-trigger"
type: trigger
stream: meta_system
status: evergreen
created_at: 2026-09-27
updated_at: 2026-09-27
tags:
  - review
  - cadences
  - execution
links:
  - "[[INDEX]]"
---

# Weekly Pulse & Delivery Review Trigger

Pemicu mingguan untuk menjaga konkurensi antar lini paralel (pekerjaan utama & side-builder) dan mencegah ide menumpuk tanpa eksekusi.

---

## 1. Triage Inbox Mentah (Maks 15 Menit)
- [ ] Jalankan `python scripts/ingest.py --all` untuk memproses seluruh file di `inbox_raw/`.
- [ ] Pastikan tidak ada catatan tertinggal di `inbox_raw/`.

---

## 2. Review Lini Konkuren (Core Work vs Side Builder)

### Core Work (Pekerjaan Utama / Klien)
- [ ] Cek status deliverable aktif di `in_motion/core_work/`.
- [ ] Identifikasi blocker teknis atau dependensi eksternal.

### Side Builder (Eksperimen, AI Agents, SaaS)
- [ ] Evaluasi progres implementasi di `in_motion/side_builder/`.
- [ ] Apakah ada prototipe yang siap dideploy atau diuji langsung?
- [ ] Jika ada pattern baru yang terbukti stabil, ekstrak ke `lattices/playbooks/`.

---

## 3. Network Health & Index Rebuild
- [ ] Jalankan `python scripts/graph_index.py build` untuk memperbarui `INDEX.md`.
- [ ] Periksa daftar **Dangling Links** di `INDEX.md` untuk mengidentifikasi topik atau modul yang perlu dibuat.
