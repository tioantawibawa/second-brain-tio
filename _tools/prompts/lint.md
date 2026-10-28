---
title: "Prompt Routine: Lint & Quality Check"
type: prompt-routine
---

# Lint Routine

## Trigger
Setelah setiap operasi ingest, atau periodik mingguan.

## Steps
1. Jalankan `python _tools/lint.py`.
2. Periksa laporan:
   - Broken `[[wikilinks]]` — file target tidak ada.
   - Orphan pages — file tanpa backlink dari manapun.
   - Missing frontmatter fields (title, type, domain, status, updated).
   - Source paths di frontmatter `sources:` yang tidak ada di `raw/`.
3. Perbaiki masalah yang terdeteksi.
4. Jalankan `python _tools/build_index.py` setelah perbaikan.
