# Manual Second Brain v2

## Penggunaan harian

Windows: klik dua kali `brain.cmd`. Linux/macOS: `python3 -m second_brain`. Buka HOME di Obsidian dan refresh melalui `home` setelah catatan berubah.

```powershell
.\brain.cmd capture "Ide atau catatan"
.\brain.cmd search "kata kunci"
.\brain.cmd plan "Ide yang perlu dijabarkan"
.\brain.cmd brief
.\brain.cmd home
.\brain.cmd health
```

Di Telegram gunakan `/help` untuk daftar perintah. Hanya akun yang dikonfigurasi pada `TELEGRAM_ALLOWED_USER_ID`, melalui private chat dengan bot, yang dapat mengakses runner. Teks/link dan audio asli disimpan sebelum diproses. File biner disimpan tanpa klaim ekstraksi otomatis.

## Dua agen

Agen 1 mengubah ide menjadi task dengan dependensi dan kriteria selesai. Agen 2 menyusun framework proposal, skill yang tersedia, dan prompt eksekusi. `/plan` atau menu 6 menyiapkan paket dan prompt orkestrasi; tempel prompt ke Codex untuk menjalankan analisis. Tio mereview proposal sebelum implementasi.

Panduan lengkap: [TASK_EXECUTION.md](TASK_EXECUTION.md).

## Konfigurasi

Pertahankan `.env` lokal/VPS dan gunakan `.env.example` sebagai acuan. Jangan salin token ke catatan atau Git. Core tidak memerlukan paket pip tambahan. Model/provider dikonfigurasi eksplisit. Fitur cloud tidak mempunyai jaminan gratis; kuota/biaya mengikuti akun provider.

Di VPS, gunakan environment proyek dari `python3 -m venv .venv`; jangan menonaktifkan proteksi package manager sistem. Hybrid indexer dan local Whisper adalah opsi terpisah, bukan dependency runner.

## Referensi operasional

- [Push kode, deploy, verifikasi live, rollback](docs/DEPLOYMENT.md)
- [Perbedaan v2 dan kompatibilitas skrip lama](docs/MIGRATION_V2.md)
- [Mulai cepat](QUICKSTART.md)

`bot --check` dan `health` adalah pemeriksaan lokal. Hasilnya tidak membuktikan Telegram/provider/VPS live sudah berfungsi. Pesan berstatus processing/uncertain perlu dicek terhadap hasil di disk sebelum dikirim ulang secara manual. Sync default hanya menampilkan status Git; push adalah tindakan eksplisit atas commit yang telah direview.
