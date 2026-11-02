# Second Brain Tio — v3

Telegram bertombol dan dashboard lokal untuk capture, pencarian, tugas, dan proposal dua agen. Workspace aktif terpisah dari kode aplikasi. Core memakai Python 3.10+ standard library; tidak perlu npm atau dependency pip tambahan.

## Buka aplikasi

Di Windows, klik dua kali **brain.cmd**. Dashboard membuka halaman Hari Ini dengan capture, inbox, tugas, dan pintasan proposal. Terminal tetap terbuka selama aplikasi dipakai.

```powershell
.\brain.cmd serve
.\brain.cmd status
.\brain.cmd task "Tinjau input laporan mingguan"
.\brain.cmd plan "Buat ringkasan mingguan satu halaman"
```

Telegram: kirim **/start** untuk menampilkan menu Beranda, Catat, Cari, Tugas, Rencanakan, Inbox, Pengetahuan, dan Sistem. Kirim **/cancel** jika ingin membatalkan input yang sedang ditunggu bot.

## Satu alur yang jelas

1. **Tangkap** — teks, URL, audio, atau dokumen masuk sebagai sumber/catatan.
2. **Temukan** — pencarian full-text lokal mengikuti catatan terbaru; tidak harus cocok seluruh kata.
3. **Rencanakan** — ide disimpan sebagai draft. Pilih Analisis dua agen untuk memakai provider AI.
4. **Review** — Agen 1 menyusun tugas/dependensi/kriteria selesai. Agen 2 menyusun framework proposal, scope, risiko, dan pertanyaan keputusan.
5. **Putuskan** — revisi atau setujui versi yang tepat. Persetujuan mengaktifkan tugas; implementasi belum berjalan otomatis.
6. **Kerjakan** — tandai task selesai, atau salin Prompt Codex beserta dokumen proposal untuk implementasi setelah persetujuan scope di chat.

Analisis dua agen adalah dua role model yang berjalan berurutan di aplikasi. Ini berbeda dari Codex subagents yang dapat dijalankan dari prompt eksternal. Draft, tugas, capture, dan pencarian tidak memerlukan AI; analisis/transkripsi cloud perlu key/model yang valid pada `.env`.

## Reset tanpa kehilangan catatan

```powershell
.\brain.cmd reset --archive
.\brain.cmd archives
.\brain.cmd restore ID_ARSIP
```

Hentikan bot/dashboard sebelum reset/restore. Reset memverifikasi snapshot lalu memilih workspace kosong; tidak menghapus file lama. Restore membuat workspace baru dan mempertahankan workspace yang ditinggalkan.

```text
.brain/
  active.json             workspace yang sedang dipakai
  workspaces/<id>/        Markdown, task/proposal SQLite, indeks pencarian
  archives/<id>/          snapshot konten lama dan manifest hash
data/telegram-state.sqlite ledger update Telegram, tidak direset
```

`.brain` diabaikan Git. Capture dan task tidak lagi mengubah catatan/log legacy yang tracked pada root. Catatan root lama tetap utuh sebagai konten legacy; tool lama yang dijalankan langsung mungkin masih membacanya. Untuk Obsidian, buka folder workspace aktif sebagai vault terpisah jika ingin melihat konten v3.

## VPS dan data lintas komputer

Service Tio: **second-brain-bot**. Entry point lama tetap menjadi wrapper ke runner baru. Tidak ada push, penghapusan ledger, atau reset VPS otomatis dari reset lokal.

Dashboard Windows memakai workspace Windows. Agar melihat data Telegram di VPS, jalankan dashboard pada VPS dan gunakan SSH tunnel. Tidak ada sinkronisasi database otomatis antar-komputer.

Panduan: [Deployment v3](docs/DEPLOYMENT_V3.md), [perubahan v3](docs/MIGRATION_V3.md), [task dua agen](TASK_EXECUTION.md), [mulai cepat](QUICKSTART.md).

## Pengujian

```bash
python -m unittest discover -s tests -p 'test_*.py' -v
python -m compileall -q second_brain
```

Tes memakai data sementara dan provider mock, bukan akun Telegram/AI live. CI Windows/Linux tersedia. Status service atau konfigurasi key saja tidak membuktikan interaksi live sudah berhasil.
