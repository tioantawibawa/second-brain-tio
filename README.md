# Second Brain Tio — Python / Telegram v2

Vault Markdown dengan satu runner Telegram, pencarian lokal, capture, analisis berbasis sumber, dan alur task dua agen. Core menggunakan Python 3.10+ standard library; tidak memerlukan npm atau paket pip tambahan.

## Mulai dari Windows

Klik dua kali **brain.cmd** untuk menu, atau jalankan:

```powershell
.\brain.cmd status
.\brain.cmd search "scoring drift"
.\brain.cmd plan "Ide yang ingin saya kerjakan"
.\brain.cmd home
.\brain.cmd health
```

Buka `HOME.md` di Obsidian. Catatan lama tetap pada lokasinya. Domain private dikecualikan dari ringkasan/pencarian secara default.

## Telegram / VPS

```bash
python3 -m second_brain --version
python3 -m second_brain bot --check  # validasi konfigurasi lokal saja
python3 -m second_brain bot          # mulai polling Telegram
```

Isi `.env` di VPS memakai `.env.example` sebagai acuan; pertahankan kredensial lama yang masih valid. Tentukan model Gemini/Groq yang benar-benar tersedia pada akun. Analisis cloud memerlukan key/model yang valid; kegagalan provider dilaporkan, tidak diganti dengan kesimpulan buatan.

| Kebutuhan | Perintah |
| --- | --- |
| Capture / catatan | teks biasa, URL, voice/audio/dokumen, `/capture`, `/journal`, `/crm` |
| Temukan kembali | `/list`, `/search`, `/read`, `/ask` |
| Fokus dan analisis | `/brief`, `/weekly`, `/warroom`, `/weave`, `/sparring`, `/ingest` |
| Dua agen | `/plan <ide>` menyiapkan prompt Agen 1 → Agen 2 → review Tio |
| Operasional | `/status`, `/sync` (status Git), `/sync push` (push eksplisit jika diaktifkan) |

`/plan` menyiapkan paket; kedua agen dijalankan saat prompt ditempel ke Codex. Implementasi menunggu review proposal. Jika paket berasal dari VPS, sinkronkan paket yang dipilih ke checkout Codex sebelum menjalankan prompt secara lokal.

## Struktur kode

```text
second_brain/
  config.py       .env dan validasi tanpa efek samping saat import
  vault.py        pembacaan Markdown, pencarian, task, HOME
  storage.py      path, penulisan catatan, provenance dan audit
  execution.py    paket ide dan prompt dua agen
  providers.py    Gemini/Groq text dan Groq/OpenAI/Gemini audio
  analysis.py     Q&A, sintesis, ingest, dan audit mingguan
  commands.py     routing perintah yang dapat diuji tanpa Telegram
  transport.py    request Telegram dan pemotongan pesan
  state.py        ledger update dan offset SQLite
  bot.py          satu runner polling dan pengamanan duplikasi
  cli.py          CLI lintas Windows/Linux
deploy/           unit systemd, update, rollback, daftar file kode
tests/            pengujian lokal tanpa kredensial/API live
```

Entry point lama `services/telegram_ingest_bot.py`, `scripts/telegram_bot.py`, dan `tools/brain.py` tetap berfungsi sebagai wrapper ke package baru. Skrip riset/konverter lama di `tools/`, `_tools/`, dan `scripts/ingest.py` tetap tersedia secara terpisah untuk kompatibilitas; tidak semuanya ditulis ulang. Pencarian hybrid lama tetap bisa dipakai dengan `tools/search.py`; neural embeddings opsional lewat `requirements-legacy.txt`.

Runner baru menyimpan update ID sebelum melakukan efek samping. Pesan yang selesai atau hasilnya tidak pasti tidak diproses ulang otomatis setelah restart. `python -m second_brain health` menampilkan hitungan `processing`/`uncertain` untuk rekonsiliasi manual. Ini mengurangi duplikasi; bukan jaminan pengiriman persis satu kali pada jaringan terputus.

## Panduan

- [Push kode dan migrasi VPS](docs/DEPLOYMENT.md)
- [Perubahan perilaku dan kompatibilitas](docs/MIGRATION_V2.md)
- [Task eksekusi dua agen](TASK_EXECUTION.md)
- [Penggunaan lokal singkat](QUICKSTART.md)

Pengujian:

```bash
python -m unittest discover -s tests -p 'test_*.py' -v
python -m compileall -q second_brain services tools scripts _tools
```

CI disiapkan untuk Windows/Linux dan Python 3.10/3.12. Kelulusan lokal tidak membuktikan CI, Telegram, provider AI, atau deployment VPS sudah berjalan.
