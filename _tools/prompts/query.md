---
title: "Prompt Routine: Query"
type: prompt-routine
---

# Query Routine

## Trigger
Pengguna mengajukan pertanyaan analitis atau permintaan sintesis.

## Steps
1. Jalankan `python tools/search.py "<query>" --top-k 5` untuk grounding.
2. Telusuri `wiki/index.md` untuk konektivitas graf.
3. Formulasi jawaban yang grounded pada vault — setiap klaim harus merujuk `[[wikilink]]`.
4. Jika menghasilkan sintesis baru: buat halaman di `wiki/<domain>/syntheses/`.
5. Tandai inferensi dengan `[Inference]`, klaim belum terkonfirmasi dengan `[Unverified]`.
6. Append ke `log.md` dengan tipe `QUERY` atau `QUERY_COMPOUND`.
