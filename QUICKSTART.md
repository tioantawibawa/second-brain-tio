# Mulai menggunakan Second Brain

Di Windows, klik dua kali **brain.cmd** untuk membuka menu. Skrip mencari Python 3.10+ yang berfungsi, termasuk runtime lokal Codex bila tersedia. Tidak perlu instal paket atau mengisi API key untuk fitur baru ini.

## Tiga kebiasaan harian

1. **Tangkap ide.** Pilih `2. Catat ide`. Catatan baru masuk ke `inbox_raw/` dan dicatat di `log.md`. Teks disimpan sesuai masukan, tanpa rangkuman atau klasifikasi AI.
2. **Temukan kembali.** Pilih `3. Cari catatan`. Gunakan kata kunci singkat. Hasil menyertakan path dan nomor baris; pencarian memerlukan semua kata di catatan yang sama.
3. **Pilih pekerjaan.** Pilih `4. Perbarui HOME.md`, lalu buka `HOME` di Obsidian. Tinjau proyek aktif, tugas terbuka, dan inbox. Centang tugas pada catatan sumber, lalu perbarui HOME.

## Perintah langsung

Jalankan PowerShell di folder vault:

```powershell
.\brain.cmd status
.\brain.cmd capture "Ide eksperimen untuk minggu depan"
.\brain.cmd capture --file "C:\catatan\meeting.txt" --title "Meeting tim"
.\brain.cmd search "scoring drift"
.\brain.cmd search "scoring" --json
.\brain.cmd home
.\brain.cmd doctor
```

Di Linux/macOS: `python3 tools/brain.py status` dan subperintah yang sama. Tanpa argumen, menu interaktif dibuka. Untuk runtime khusus pada Windows:

```powershell
$env:SECOND_BRAIN_PYTHON = 'C:\path\ke\python.exe'
.\brain.cmd doctor
```

## Dari ide menjadi task eksekusi

Pilih **6. Task eksekusi** pada menu, atau jalankan:

```powershell
.\brain.cmd plan "Ide yang ingin saya kerjakan" --domain work
```

Perintah menyiapkan paket dan langsung menampilkan prompt orkestrasi. Salin ke Codex untuk menjalankan **Agen 1** (pemecahan tugas) lalu **Agen 2** (framework proposal, skill, dan prompt eksekusi). Tio mereview proposal sebelum implementasi. Lihat [TASK_EXECUTION.md](TASK_EXECUTION.md) untuk alur lengkap. Paket awal berstatus pending; tidak ada panggilan AI otomatis dari CLI.

## Apa yang dihitung

- Proyek aktif hanya catatan `in_motion/` dan `wiki/<domain>/projects/` dengan `status: active` pada frontmatter. Catatan deployed, evergreen, dan tanpa status tidak diasumsikan sebagai pekerjaan aktif.
- Tugas hanya checkbox terbuka dari proyek aktif; contoh dalam blok kode dikecualikan. Nomor baris menunjuk file sumber.
- Inbox menghitung Markdown dalam `inbox_raw/`, selain arsip `processed/`. `raw/` tetap tersedia untuk pencarian tetapi tidak dihitung sebagai antrean inbox.
- HOME adalah snapshot, bukan pembaruan otomatis. Batas tampilan: 30 tugas, 15 inbox, 8 catatan terbaru. Urutan tugas bukan peringkat prioritas.
- `doctor` membaca kondisi folder dan waktu modifikasi indeks hybrid. Pemeriksaan ini tidak memvalidasi layanan Telegram/VPS atau isi seluruh database.

## Privasi dan kompatibilitas

Fitur baru berjalan lokal dan tidak membaca `.env` atau memanggil layanan eksternal. Path di `private/` dan catatan dengan `domain: private` dikecualikan dari HOME, status, dan pencarian secara default. Untuk pencarian terminal pribadi, tambahkan `--include-private`. Catatan lama yang sensitif tetapi belum diberi domain/path private tidak dapat dikenali otomatis; HOME tetap bersifat lokal dan tidak boleh dipublikasikan sembarangan.

Pencarian baru membaca Markdown saat dijalankan sehingga tidak bergantung pada indeks SQLite. Ini pencarian kata kunci, bukan pencarian semantik. Mesin hybrid lama (`tools/search.py`) tetap tersedia; indeksnya diperbarui lewat `tools/indexer.py`. Model embedding opsional pada alur lama dapat memerlukan unduhan.

Pemrosesan AI/Telegram tetap memakai skrip lama dan konfigurasi terpisah. Capture tidak memicu ingest otomatis. HOME tidak menggantikan `index.md`. Jika `HOME.md` sudah berisi tulisan pengguna, generator menolak menimpanya. Frontmatter reader fitur baru hanya membaca field scalar tingkat atas, bukan seluruh fitur YAML.

## Pemeriksaan pengembang

```powershell
.\brain.cmd doctor
# Dengan executable Python yang valid:
python -m unittest discover -s tests -p test_brain.py -v
```

Lihat [docs/MIGRATION_V2.md](docs/MIGRATION_V2.md) untuk perubahan perilaku v2 dan batas verifikasi, serta [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) untuk push GitHub dan update VPS.
