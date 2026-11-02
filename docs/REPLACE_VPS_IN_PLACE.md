# Ganti Second Brain langsung di folder VPS yang sama

Folder tetap: **/home/ubuntu/second-brain**. Service tetap: **second-brain-bot**. Tidak perlu membuat checkout lain.

Helper mengganti hanya file kode/dokumentasi pada allowlist commit `origin/main`. Ia menerima checkout dengan riwayat Git divergen atau log/catatan lokal yang berubah karena tidak melakukan pull, merge, reset riwayat, atau push.

## 1. Buka SSH VPS

Jalankan dari akun `ubuntu`, bukan PowerShell Windows atau `sudo python`:

```bash
cd /home/ubuntu/second-brain
git fetch origin main
replace_script=$(mktemp /tmp/second-brain-replace.XXXXXX.py)
git show origin/main:deploy/replace_vps.py > "$replace_script"
```

Jika salah satu perintah gagal, berhenti dan kirim errornya. Hentikan cron/proses manual lain yang menulis vault; helper menghentikan bot dan menolak jika lock dashboard/bot lain masih digunakan.

## 2. Ganti kode dan mulai workspace bersih dengan arsip

```bash
python3 "$replace_script" --repo "$PWD" --service second-brain-bot --reset-workspace
```

Helper akan:

1. Memastikan remote benar dan mengambil snapshot file kode dari commit GitHub yang tetap.
2. Menyiapkan `.venv`, lalu menghentikan service.
3. Menyimpan backup kode, data termasuk `.brain`, `.env`, dan unit lama di `/home/ubuntu/second-brain-backups/inplace-TIMESTAMP/`.
4. Mengganti kode pada folder **yang sama**, mempertahankan `.env`, data asli, ledger Telegram, dan riwayat Git.
5. Menjalankan tests dan validasi konfigurasi bot.
6. Mengarsipkan konten aktif dan memilih workspace kosong karena flag `--reset-workspace` diberikan.
7. Memasang unit yang menunjuk `/home/ubuntu/second-brain/.venv/bin/python -m second_brain bot`, lalu menyalakan service.

Simpan path backup dan SHA source yang dicetak. Hapus flag `--reset-workspace` untuk penggantian kode berikutnya yang harus mempertahankan workspace aktif. Jangan mengulang reset setelah mulai mengisi catatan baru kecuali memang ingin mengarsipkannya lagi.

Jika `python3-venv` belum tersedia, helper gagal sebelum menghentikan bot. Instal paket tersebut pada VPS, kemudian ulangi. Jika kegagalan terjadi setelah bot dihentikan, baca lokasi backup dan instruksi rollback yang dicetak; bot tidak dianggap berhasil hanya karena perintah sudah dijalankan.

## 3. Verifikasi

```bash
cd /home/ubuntu/second-brain
.venv/bin/python -m second_brain --version
.venv/bin/python -m second_brain status
sudo systemctl show second-brain-bot -p WorkingDirectory -p ExecStart
sudo systemctl status second-brain-bot --no-pager
sudo journalctl -u second-brain-bot -n 60 --no-pager -l
```

Versi harus **3.0.0**, path service tetap **/home/ubuntu/second-brain**, dan service **active (running)**. Jika reset dipilih, status awal menunjukkan 0 catatan/tugas/proposal dan setidaknya satu arsip. Pada Telegram, kirim `/start` untuk membuka menu baru, lalu uji Catat, Cari, Tugas, dan Rencanakan.

Untuk dashboard di VPS yang sama:

```bash
cd /home/ubuntu/second-brain
.venv/bin/python -m second_brain serve --no-open --port 8767
```

Pada PowerShell Windows (ganti `IP_VPS` dengan alamat sebenarnya):

```powershell
ssh -N -L 8767:127.0.0.1:8767 ubuntu@IP_VPS
```

Buka URL sesi persis dari terminal dashboard, dengan port 8767. Token URL adalah sesi dashboard, bukan token Telegram. Tidak perlu membuka port dashboard ke internet.

## 4. Rollback jika diperlukan

Ganti `PATH_BACKUP` dengan direktori backup nyata yang dicetak:

```bash
cd /home/ubuntu/second-brain
python3 deploy/replace_vps.py --repo "$PWD" --service second-brain-bot --rollback PATH_BACKUP
```

Rollback mengembalikan kode/unit dan pointer workspace sebelum penggantian. Direktori arsip/workspace baru tetap disimpan, sehingga catatan baru tidak dihapus. `.env` tetap pada nilai terkini. Backup data lengkap tersedia di `data-before.tgz` jika perlu pemulihan data terpisah; jangan menimpanya ke atas data aktif tanpa pemeriksaan.

## Status Git setelah penggantian

Riwayat dan HEAD Git VPS dipertahankan. Karena kode diganti dari snapshot GitHub, `git status` dapat memperlihatkan perubahan kode terhadap HEAD VPS lama; ini disengaja. SHA kode terpasang dicatat di `.brain/release.json` dan dicetak helper. Untuk pembaruan in-place berikutnya, gunakan helper ini tanpa flag reset; `git pull --ff-only` tetap dapat menolak histori VPS lama yang divergen.

Panduan/helper ini belum dijalankan pada VPS oleh Codex. Verifikasi Telegram, provider AI, cron, dan akses SSH dilakukan pada VPS sebenarnya setelah Tio menjalankannya.
