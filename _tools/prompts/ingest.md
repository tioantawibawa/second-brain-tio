---
title: "Prompt Routine: Ingest"
type: prompt-routine
---

# Ingest Routine

## Trigger
File baru terdeteksi di `raw/` (belum ada di `raw/processed/`).

## Steps
1. Baca file sumber di `raw/<filename>`.
2. Tentukan domain: `work`, `engineering`, atau `private`.
3. Ekstrak: Core Insight, Entitas Kunci, Tools/Library, Action Items.
4. Buat/update halaman di `wiki/<domain>/topics/<slug>.md` atau `wiki/<domain>/sources/<slug>.md`.
5. Jika ada orang/entitas: buat/update di `wiki/<domain>/people/<nama>.md` atau `crm/`.
6. Update `wiki/index.md` via `python _tools/build_index.py`.
7. Append ke `log.md` dengan tipe `INGEST`.
8. Pindahkan sumber ke `raw/processed/`.
9. Jalankan `python _tools/lint.py` untuk verifikasi.

## Principles
- Source before memory: selalu kutip dokumen, bukan ingatan.
- Tandai kesimpulan sendiri dengan `[Inference]`.
- Tandai klaim belum terkonfirmasi dengan `[Unverified]`.
