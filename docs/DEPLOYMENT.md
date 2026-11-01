# Push kode ke GitHub dan perbarui VPS

Remote yang dituju: `https://github.com/tioantawibawa/second-brain-tio`, branch `main`. Instruksi ini dijalankan Tio setelah meninjau perubahan. Rewrite lokal tidak otomatis memperbarui GitHub atau VPS.

## 1. Periksa dan push dari Windows

```powershell
Set-Location 'C:\Users\tio\.gemini\antigravity\scratch\second-brain'
git remote -v
git status --short
.\brain.cmd --version
.\brain.cmd health
```

Stage hanya file kode yang tercantum di `deploy/code-files.txt`:

```powershell
.\scripts\stage_release.ps1
git diff --cached --stat
git diff --cached
git commit -m "refactor: modular Python Telegram runner and VPS deployment"
git fetch origin main
git rebase --autostash origin/main
git push origin main
```

`--autostash` mempertahankan perubahan tracked yang belum dicommit, termasuk audit log lokal, selama rebase. Jika rebase atau penerapan autostash konflik, selesaikan secara eksplisit sebelum push; simpan stash sampai isi catatan dipastikan utuh. Tidak perlu force push. Helper stage menolak berjalan jika sebelumnya sudah ada perubahan staged, supaya commit kode tidak menyertakan staged data tanpa sengaja. Helper tidak menjalankan commit/push. `HOME.md`, `log.md`, catatan vault baru, raw audio, file Untitled, dan kerangka Node yang belum lengkap tidak ditambahkan oleh helper. Catatan yang sudah tracked di riwayat Git tetap tracked; ini bukan pembersihan riwayat atau perubahan visibilitas repository.

GitHub Actions akan menjalankan pengujian pada push. Periksa hasil run; konfigurasi CI di repository bukan bukti run sudah lulus.

## 2. Pemeriksaan awal pada VPS

Jalankan dengan user pemilik checkout, misalnya `ubuntu`. Path `/home/ubuntu/second-brain` berasal dari unit lama; konfirmasi path aktual sebelum memakai contoh ini.

```bash
cd /home/ubuntu/second-brain
pwd
git remote -v
git status --short
systemctl show secondbrain-telegram -p WorkingDirectory -p ExecStart
systemctl status secondbrain-telegram --no-pager
systemctl status second-brain-bot --no-pager
crontab -l
```

Pilih satu service yang benar. Jika service lain aktif untuk checkout yang sama, stop/disable duplikat setelah memeriksa `WorkingDirectory`; jangan menjalankan dua poller untuk token yang sama. Tinjau cron lama yang mungkin masih memanggil skrip analisis/sync. Script update menolak checkout dengan perubahan tracked yang belum dicommit atau histori yang divergen. Commit/salin perubahan vault yang diperlukan sebelum melanjutkan; tidak ada `git reset --hard` atau `git clean`.

Simpan `.env` di VPS. Gunakan `.env.example` sebagai daftar field, jangan menimpa `.env` lama secara otomatis. Periksa nilai `GEMINI_MODEL`/`GROQ_MODEL` terhadap akun provider; runner baru tidak mencoba daftar model tebakan. Sync Git otomatis default nonaktif. Pada Ubuntu, paket `python3-venv` perlu tersedia agar environment bisa dibuat; bila belum tersedia, instal lewat package manager dengan akses administrator.

## 3. Jalankan update dengan backup

Untuk deployment pertama ketika script baru belum ada pada checkout VPS:

```bash
cd /home/ubuntu/second-brain
git fetch origin main
update_script=$(mktemp /tmp/second-brain-update.XXXXXX.sh)
git show origin/main:deploy/update_vps.sh > "$update_script"
# Tinjau script sebelum menjalankan:
cat "$update_script"
bash "$update_script" "$PWD" secondbrain-telegram
```

Script memvalidasi remote/branch dan perubahan lokal, menghentikan service yang dipilih, menyimpan backup kode/vault/state/env/unit pada direktori sibling `second-brain-backups/`, lalu merge fast-forward, membuat `.venv`, menjalankan tests dan pemeriksaan konfigurasi, serta memasang/restart satu unit. Tes tidak memanggil provider/Telegram live. Backup dibuat setelah writer berhenti. Service lama tidak otomatis dinyalakan kembali jika langkah deployment gagal; baca error dan gunakan rollback agar kegagalan tidak tersembunyi.

Script hanya menangani unit systemd yang dipilih. Hentikan writer lain yang sudah ditemukan di langkah sebelumnya agar backup dan deployment tidak bersaing dengan cron atau proses manual. Gunakan nama service kedua sebagai argumen jika memang itu unit yang dipertahankan.

## 4. Verifikasi live

```bash
sudo systemctl status secondbrain-telegram --no-pager
sudo journalctl -u secondbrain-telegram -n 60 --no-pager
.venv/bin/python -m second_brain --version
.venv/bin/python -m second_brain bot --check
.venv/bin/python -m second_brain health
git rev-parse HEAD
```

Lalu dari akun Telegram yang diizinkan, kirim `/status`, satu capture uji, `/search`, `/read`, dan `/plan` dengan ide yang memang ingin direncanakan. Periksa artefak di disk. Uji voice serta `/ask` setelah konfigurasi provider benar. Status `active` systemd saja bukan bukti pesan atau transkripsi berhasil.

## 5. Rollback kode/unit

Gunakan lokasi backup yang dicetak script. Salin rollback helper ke file sementara agar restore kode tidak mengganti script yang sedang dibaca:

```bash
rollback_script=$(mktemp /tmp/second-brain-rollback.XXXXXX.sh)
cp deploy/rollback_vps.sh "$rollback_script"
bash "$rollback_script" /home/ubuntu/second-brain-backups/TIMESTAMP-SHA
```

Ganti argumen terakhir dengan direktori backup nyata. Helper memeriksa manifest/path, menghentikan service, mengembalikan isi kode dan unit lama, mempertahankan `.env` dan vault/state terkini, lalu menyalakan kembali service jika sebelumnya aktif. Git HEAD tetap pada commit hasil deployment; working tree memperlihatkan isi rollback sebagai perubahan. Ini rollback isi file, bukan reset riwayat. File baru v2 yang tidak ada pada backup boleh tetap di disk dan tidak digunakan oleh entry point lama.

Jika unit lama tidak ada pada backup (deployment pertama), helper menolak rollback otomatis. Nonaktifkan unit baru dan pulihkan kode secara manual dari `code-before.tgz` setelah memeriksa isinya. Snapshot `vault-before.tgz` dan `env-before` disediakan untuk pemulihan terpisah; jangan menimpa vault terbaru hanya untuk membatalkan perubahan kode.
