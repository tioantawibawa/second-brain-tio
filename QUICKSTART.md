# Mulai cepat — Second Brain v3

1. Klik dua kali **brain.cmd** untuk membuka dashboard. Biarkan terminal terbuka.
2. Simpan satu catatan lewat Hari Ini atau Catat pada Telegram.
3. Tambahkan satu task di halaman Tugas; tandai selesai ketika sudah dikerjakan.
4. Ceritakan ide di Proposal & Agen. Draft tetap tersimpan tanpa AI. Tekan Analisis dua agen saat provider siap, lalu review proposal sebelum mengaktifkan tugas.
5. Salin Prompt Codex bila ingin melanjutkan implementasi. Sertakan dokumen proposal dan scope yang Tio setujui secara langsung.

Telegram: **/start** membuka tombol menu, **/help** memberi panduan, **/cancel** membatalkan input. Fitur AI lama seperti /ask, /ingest, /weave, /warroom, /sparring dan /weekly tetap tersedia.

Reset lokal awal sudah dijalankan sesuai permintaan. Workspace aktif kosong, catatan lama ada dalam arsip terverifikasi dan sumber legacy tetap utuh. Daftar arsip: `brain.cmd archives`. Pemulihan: `brain.cmd restore ID_ARSIP` saat bot/dashboard dihentikan.

Data baru disimpan di `.brain/` dan tidak ikut Git. Cadangkan folder ini secara privat. Jangan menghapus `data/telegram-state.sqlite` untuk reset catatan.

Dashboard pada komputer ini tidak otomatis menampilkan data VPS. Lihat [deployment v3](docs/DEPLOYMENT_V3.md) untuk SSH tunnel dan migrasi service **second-brain-bot** tanpa menggabungkan riwayat Git lama secara paksa.
