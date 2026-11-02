# Apa yang berubah pada v3

- **Workspace bersih:** reset mengarsipkan konten lama dan memilih folder aktif baru. Root legacy tetap utuh; aplikasi baru hanya membaca workspace yang dipilih.
- **Kode terpisah dari data:** `.brain/active.json` menunjuk `.brain/workspaces/<id>/`; arsip berada di `.brain/archives/<id>/`. Folder `.brain` diabaikan Git. Tidak ada git add/commit/push otomatis dari capture/task.
- **Dashboard lokal:** Hari Ini, Inbox, Pengetahuan, Tugas, Proposal & Agen, Sistem. URL sesi hanya untuk mesin sendiri; API memerlukan token per proses dan origin lokal yang sesuai.
- **Telegram bertombol:** menu utama, input bertahap, pembatalan, tombol selesai task, analisis, review, dan persetujuan. Sesi input tersimpan 15 menit dan dapat dilanjutkan setelah restart.
- **Tugas nyata:** task persisten dengan state todo/doing/done. Persetujuan proposal menambahkan task secara idempoten; draft bukan pekerjaan aktif.
- **Dua peran AI berurutan:** panggilan model pertama memecah ide menjadi tugas tervalidasi; panggilan kedua menerima hasilnya untuk proposal. Ini dua role dalam aplikasi, bukan dua Codex subagent yang diam-diam berjalan di VPS. Implementasi dilakukan terpisah melalui prompt Codex.
- **Review berversi:** proposal bisa direvisi sebelum disetujui. Tombol persetujuan lama tidak boleh menyetujui versi baru. Setelah approved, perubahan scope dibuat sebagai draft baru; task yang sudah aktif dipertahankan.
- **Pemulihan kegagalan:** hasil Agen 1 disimpan sebelum Agen 2 dijalankan; kegagalan Agen 2 dapat dilanjutkan tanpa mengulangi Agen 1. Proposal yang sudah siap tidak dianalisis ulang setiap tombol ditekan.
- **Pencarian lebih fleksibel:** indeks full-text lokal, kata parsial antarkonsep, refresh catatan yang berubah/dihapus. Jika SQLite tanpa FTS5, gunakan ranking keyword fallback. Tidak diklaim sebagai pencarian neural/semantik.
- **Kompatibilitas:** analisis, transkripsi, journal, CRM, dan ingest v2 tetap tersedia. Tool lama yang dijalankan langsung mungkin masih membaca root legacy; gunakan entry point `brain.cmd`/`python -m second_brain` untuk workspace v3.

Persiapan draft, capture, tugas, pencarian, dan dashboard tidak memerlukan AI. Analisis dua agen/AI membutuhkan provider/model yang benar; tidak ada key/model yang ditebak atau diisi ulang. `.env` lama tidak dimodifikasi. Data pribadi tidak diarsipkan ke hosting eksternal.

Dashboard/bot harus dihentikan sebelum reset atau restore. Lock proses menolak pergantian workspace ketika layanan yang sesuai masih aktif. Ledger Telegram disimpan pada level proyek dan tidak direset agar update lama tidak diputar ulang. Arsip diverifikasi melalui checksum sebelum pointer workspace dipindahkan.

Keterbatasan: workspace Windows dan VPS terpisah. Untuk melihat data VPS pada browser lokal gunakan SSH tunnel, bukan mengasumsikan data sudah tersinkron. Prompt Codex dari VPS perlu disertai dokumen proposal yang bisa dibaca sesi Codex. Versi awal ini tidak melakukan eksekusi shell arbitrer, scheduling otomatis tugas, atau implementasi proyek hanya karena proposal disetujui.
