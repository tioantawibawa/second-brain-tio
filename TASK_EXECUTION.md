# Task eksekusi — Second Brain v3

## Cara mulai

Telegram: tekan **Rencanakan**, lalu tulis ide. Dashboard: buka **Proposal & Agen**, isi ide dan buat draft. CLI: `brain.cmd plan "Ide saya"`.

Draft tidak memanggil model. Tekan **Analisis dua agen** atau jalankan `brain.cmd planrun P-ID` untuk memakai provider AI yang dikonfigurasi.

| Tahap | Peran | Hasil |
| --- | --- | --- |
| Draft | Tio | Ide asli tersimpan |
| Agen 1 | Pemecahan tugas | ID, output, kriteria selesai, dependensi yang valid |
| Agen 2 | Proposal reviewer | Framework, scope, risiko, rekomendasi, pertanyaan keputusan |
| Review | Tio | Revisi atau persetujuan versi tertentu |
| Aktivasi | Aplikasi | Tugas masuk daftar aktif; belum ada implementasi otomatis |
| Eksekusi | Codex / Tio | Prompt dan proposal digunakan setelah persetujuan scope langsung di chat |

Peran AI di aplikasi adalah dua panggilan model berurutan, bukan dua proses Codex yang berjalan tersembunyi. Proposal disimpan di SQLite workspace dan diekspor ke `wiki/work/projects/p-ID.md`. Hasil Agen 1 dipertahankan jika Agen 2 gagal; gunakan Analisis dua agen lagi untuk melanjutkan. Hasil yang sudah siap tidak dipanggil ulang setiap dibuka.

## Review dan revisi

Tombol persetujuan terikat versi. Tombol lama tidak dapat menyetujui proposal yang direvisi. Persetujuan hanya mengaktifkan task, bukan menjalankan shell/kode.

```text
/plans
/proposal P-ID
/revise P-ID Batasi ke prototipe lokal
/approve P-ID 1
/prompt P-ID
```

Ganti ID dan versi dengan nilai nyata dari proposal. Revisi sebelum approved menghasilkan versi baru. Jika scope berubah setelah approved, buat draft baru agar task lama tetap tercatat.

## Prompt dan skill Codex

Prompt tersedia melalui tombol **Prompt Codex**. Jika proposal berasal dari VPS, salin juga dokumen proposal ke checkout yang dapat dibaca Codex. Skill lokal `second-brain-execution` tetap menjadi referensi perencanaan; skill implementasi dipilih sesuai deliverable dan ketersediaan pada sesi Codex. Tidak ada klaim bahwa skill tambahan otomatis terpasang.

Mode kompatibilitas lama: `brain.cmd plan "ide" --legacy-packet`, atau `--domain private/engineering`, tetap bisa menyiapkan paket Markdown lima file tanpa menjalankan provider. Paket private tidak diikutkan ke dashboard umum.
