# Second Brain v3 — push kode, reset workspace, dan VPS

Reset aplikasi tidak mempublikasikan kode dan tidak mengubah VPS. Data aktif dan arsip baru berada di `.brain/`, di luar tracking Git. `.env` dan ledger Telegram dipertahankan. Nama service VPS Tio yang terkonfirmasi: `second-brain-bot`.

## Windows: mulai menggunakan

Klik dua kali `brain.cmd` untuk membuka dashboard lokal. Atau:

```powershell
Set-Location 'C:\Users\tio\.gemini\antigravity\scratch\second-brain'
.\brain.cmd --version
.\brain.cmd serve
```

Biarkan terminal terbuka. `Ctrl+C` menghentikan dashboard. URL sesi dicetak di terminal; jangan bagikan URL tersebut. Server hanya mendengarkan `127.0.0.1`, bukan internet.

Reset lokal yang diminta Tio sudah dijalankan saat pemasangan. Untuk reset berikutnya, hentikan dashboard/bot lokal terlebih dahulu:

```powershell
.\brain.cmd archives
.\brain.cmd reset --archive
```

`reset --archive` menyalin konten workspace aktif ke arsip terverifikasi lalu memilih workspace kosong. File lama tidak dihapus. Untuk pemulihan, gunakan ID yang benar dari `archives`:

```powershell
.\brain.cmd restore ID_ARSIP
```

Restore membuat workspace baru, memverifikasi hash arsip, dan tidak menimpa workspace yang ditinggalkan.

## Push kode dari Windows

```powershell
.\scripts\stage_release.ps1
git diff --cached --stat
git diff --cached
git commit -m "feat: Second Brain v3 workspace, Telegram menus and local dashboard"
git fetch origin main
git rebase --autostash origin/main
git push origin main
```

Review konflik jika ada; jangan force push. Helper stage hanya file kode yang diizinkan. `.brain`, `.env`, log/catatan legacy, dan file data tidak ikut ditambahkan. Notes lama yang sudah tracked pada riwayat tetap tracked; reset ini bukan perubahan riwayat atau visibilitas repository. CI disiapkan, tetapi hasil run GitHub harus diperiksa terpisah.

## VPS: jalur yang dianjurkan untuk riwayat lama yang divergen

Karena checkout VPS sebelumnya mempunyai merge lokal dan catatan yang belum dicommit, gunakan checkout kode baru. Checkout lama tetap utuh untuk cadangan. Jalankan setelah commit v3 benar-benar tersedia di GitHub:

```bash
sudo systemctl stop second-brain-bot
# Hentikan juga cron/proses manual lain yang masih menulis ke vault lama.
cd ~
git clone --branch main --single-branch https://github.com/tioantawibawa/second-brain-tio.git second-brain-v3
cp -p ~/second-brain/.env ~/second-brain-v3/.env
cd ~/second-brain-v3
python3 -m second_brain --version
python3 -m second_brain reset --archive --source ~/second-brain
python3 -m second_brain bot --check
bash deploy/update_vps.sh "$PWD" second-brain-bot
```

Gunakan nama checkout baru yang belum ada. Jika clone gagal, jangan melanjutkan ke copy/reset. Perintah reset dengan `--source` mengarsipkan konten aktual checkout lama, termasuk file yang belum tracked, dan menyalin ledger Telegram jika belum ada di tujuan. Workspace baru tetap kosong. Kredensial dipindahkan melalui copy `.env` secara lokal pada VPS, tidak dicetak atau masuk Git. Library local Whisper dan environment khusus lama perlu dipasang ulang bila digunakan.

Script update memasang unit `second-brain-bot` ke path checkout baru dengan `.venv`, tests, config check, backup dan restart. Checkout lama tidak di-reset/dihapus. Jika langkah gagal setelah service dihentikan, periksa log dan hidupkan kembali service dengan unit lama sebelum mencoba ulang. Tidak ada konfirmasi live VPS dalam pekerjaan lokal ini.

## Verifikasi Telegram

```bash
sudo systemctl status second-brain-bot --no-pager
sudo journalctl -u second-brain-bot -n 60 --no-pager -l
```

Kirim `/start` ke bot. Menu utama harus menampilkan Beranda, Catat, Cari, Tugas, Rencanakan, Inbox, Pengetahuan, dan Sistem. Uji capture, pencarian, tambah tugas, selesai tugas, dan buat draft. Jalankan Analisis dua agen hanya setelah provider/model yang valid dikonfigurasi. Hasil mock lokal bukan bukti model/provider live berfungsi.

## Dashboard untuk data VPS

Dashboard yang dijalankan di Windows memakai data Windows. Agar dashboard lokal melihat workspace VPS yang sama dengan bot, jalankan server di VPS:

```bash
cd ~/second-brain-v3
.venv/bin/python -m second_brain serve --no-open --port 8765
```

Lalu buka tunnel dari PowerShell Windows (ganti `IP_VPS` dengan alamat sebenarnya):

```powershell
ssh -L 8765:127.0.0.1:8765 ubuntu@IP_VPS
```

Buka URL `http://127.0.0.1:8765/#...` yang dicetak server VPS. Jangan gunakan port lokal yang sama dengan dashboard Windows lain yang masih aktif. Dashboard dan bot bisa berjalan bersama pada workspace VPS yang sama. Tidak ada sinkronisasi otomatis database antar-komputer dan tidak perlu membuka port 8765 ke internet.

## Backup dan rollback

Data aktif dan arsip: backup folder `.brain` secara privat. Ledger Telegram: `data/telegram-state.sqlite`; jangan menghapusnya saat reset. `.env` dicadangkan terpisah, bukan ke Git publik. Script deploy memisahkan `.brain` dari backup kode agar rollback kode tidak menimpa catatan terbaru.

Unit sebelum migrasi dan code snapshot disimpan oleh `deploy/update_vps.sh`; ikuti bagian rollback pada [panduan v2](DEPLOYMENT_V2.md) dengan nama service **second-brain-bot** dan direktori backup nyata. Setelah restore unit lama, periksa `WorkingDirectory`/`ExecStart` sebelum restart agar runner kembali memakai checkout yang dimaksud.
