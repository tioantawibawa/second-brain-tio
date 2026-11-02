# Memperbarui Second Brain di VPS ke v3

Target: `tioantawibawa/second-brain-tio`, branch `main`. Service yang sudah ada: **second-brain-bot**. Checkout lama: **/home/ubuntu/second-brain**.

Gunakan checkout baru agar riwayat Git VPS yang sebelumnya divergen tidak perlu di-reset atau dipaksa merge. Catatan lama diarsipkan, workspace v3 mulai kosong, dan checkout lama tetap utuh. Dashboard Windows dan VPS memakai data masing-masing.

## 1. Siapkan kode baru — bot lama tetap berjalan

Jalankan di terminal VPS `ubuntu@VM-0-5-ubuntu`:

```bash
cd /home/ubuntu
git clone --branch main --single-branch https://github.com/tioantawibawa/second-brain-tio.git second-brain-v3
```

Jika folder `second-brain-v3` sudah ada atau clone gagal, berhenti di sini; jangan hapus folder atau lanjutkan ke langkah berikutnya. Periksa isinya atau gunakan nama folder baru dan sesuaikan seluruh path berikut.

```bash
cd /home/ubuntu/second-brain-v3
python3 -m venv .venv
cp -p /home/ubuntu/second-brain/.env .env
.venv/bin/python -m second_brain --version
.venv/bin/python -m second_brain bot --check
```

Lanjutkan hanya jika versi menunjukkan **3.0.0** dan konfigurasi bot valid. Pemeriksaan ini tidak menguji token ke Telegram atau model AI. Jika pembuatan venv gagal karena paket belum tersedia, instal `python3-venv` melalui package manager VPS, lalu ulangi pembuatan venv.

## 2. Hentikan writer lama dan arsipkan catatannya

Hentikan juga cron/proses manual lain yang masih menulis ke checkout lama. Jangan memulai bot Windows dengan token yang sama.

```bash
cd /home/ubuntu/second-brain-v3
mkdir -p tmp/migration-backup
sudo systemctl cat second-brain-bot > tmp/migration-backup/service-before.service
sudo systemctl stop second-brain-bot
.venv/bin/python -m second_brain reset --archive --source /home/ubuntu/second-brain
.venv/bin/python -m second_brain archives
.venv/bin/python -m second_brain status
```

Perintah reset menyalin konten aktual checkout lama, termasuk catatan yang belum tracked, ke arsip terverifikasi. Sumber lama tidak dihapus. Ledger Telegram disalin ke checkout baru jika belum ada, agar update lama tidak diproses ulang. Status workspace baru seharusnya **0 catatan, 0 tugas, 0 proposal** dan setidaknya satu arsip.

Jika reset gagal, jangan lanjut deploy. Nyalakan kembali service lama dengan `sudo systemctl start second-brain-bot`, lalu periksa error. Jangan mengulangi reset jika sudah berhasil dan Tio mulai mengisi workspace baru.

## 3. Pasang service v3

```bash
cd /home/ubuntu/second-brain-v3
bash deploy/update_vps.sh "$PWD" second-brain-bot
```

Script menjalankan tests, memeriksa konfigurasi, menyimpan backup, lalu mengarahkan unit systemd ke `/home/ubuntu/second-brain-v3/.venv/bin/python`. Simpan direktori backup yang dicetak. Jika script gagal, berhenti dan lihat pesan error; jangan memakai `git reset --hard`.

## 4. Periksa service dan Telegram

```bash
sudo systemctl show second-brain-bot -p WorkingDirectory -p ExecStart
sudo systemctl status second-brain-bot --no-pager
sudo journalctl -u second-brain-bot -n 60 --no-pager -l
```

`WorkingDirectory` harus menunjuk **/home/ubuntu/second-brain-v3**, dan status service **active (running)**. Kemudian kirim dari akun Telegram yang diizinkan:

```text
/start
/status
/capture Catatan pertama di workspace v3
/search pertama
/task Periksa menu Second Brain
/tasks
```

Menu harus menampilkan Beranda, Catat, Cari, Tugas, Rencanakan, Inbox, Pengetahuan, dan Sistem. Capture harus ditemukan lewat pencarian dan task dapat ditandai selesai.

Untuk alur dua agen, tekan **Rencanakan**, tulis ide, lalu **Analisis dua agen**. Tahap ini memerlukan provider/model valid. Periksa proposal sebelum menyetujui; persetujuan mengaktifkan tugas dan tidak menjalankan implementasi otomatis. Tidak perlu memasang dependency tambahan untuk core atau memakai npm.

## 5. Dashboard lokal untuk workspace VPS yang sama

Pada terminal VPS kedua:

```bash
cd /home/ubuntu/second-brain-v3
.venv/bin/python -m second_brain serve --no-open --port 8767
```

Biarkan terminal itu terbuka dan simpan URL sesi yang dicetak. Di PowerShell Windows, buka tunnel (ganti `IP_VPS` dengan IP/hostname VPS yang sebenarnya):

```powershell
ssh -N -L 8767:127.0.0.1:8767 ubuntu@IP_VPS
```

Buka URL sesi persis seperti yang dicetak server, misalnya `http://127.0.0.1:8767/#TOKEN_SESI`. Gunakan token sesi dashboard, bukan token BotFather. Port 8767 dipilih pada kedua sisi agar tidak bertabrakan dengan dashboard Windows pada 8765 dan agar pemeriksaan Host tetap cocok. Jangan buka port dashboard ke internet. `Ctrl+C` menutup tunnel/server terminal.

## 6. Jika perlu kembali ke bot lama

Checkout dan `.env` lama tetap berada di `/home/ubuntu/second-brain`. Pulihkan unit yang disalin sebelum migrasi:

```bash
sudo systemctl stop second-brain-bot
sudo install -m 644 /home/ubuntu/second-brain-v3/tmp/migration-backup/service-before.service /etc/systemd/system/second-brain-bot.service
sudo systemctl daemon-reload
sudo systemctl start second-brain-bot
sudo systemctl show second-brain-bot -p WorkingDirectory -p ExecStart
sudo systemctl status second-brain-bot --no-pager
```

Pastikan unit kembali menunjuk checkout lama. Workspace dan arsip v3 tetap disimpan; jangan hapus keduanya untuk rollback kode. Jika unit memiliki drop-in tambahan, periksa `systemctl cat second-brain-bot` agar override tidak tetap mengarahkan ke path baru.
