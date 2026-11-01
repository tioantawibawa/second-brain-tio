# Migrasi v2

## Yang dipertahankan

- Folder vault, catatan, raw source, indeks lama, `.env`, dan konfigurasi Obsidian.
- Launcher Windows, HOME, capture, search, doctor, dan task dua agen.
- Perintah Telegram untuk capture, voice/audio, dokumen, journal, CRM, baca/cari, Q&A, brief, weekly, WEAVE, War Room, sparring, ingest, dan sync.
- Entry point lama bot sebagai wrapper; systemd lama masih bisa memanggil path tersebut sampai unit diperbarui.
- Tool hybrid search, indexer, converter, lint, serta CLI eksperimen lama tetap ada sebagai jalur kompatibilitas.

## Perubahan yang perlu diketahui

| Sebelumnya | v2 |
| --- | --- |
| Dua implementasi polling; fallback dapat menjalankan runner lain | Satu runner shared, lock per vault, ledger SQLite |
| Beberapa kegagalan AI diganti hasil heuristik yang terdengar final | Runner baru melaporkan kegagalan tanpa kesimpulan fiktif |
| Cascade nama model hardcoded dan klaim free | Provider text memakai model/fallback eksplisit di `.env`; biaya/kuota mengikuti akun |
| `/sync` dan weekly dapat stage/commit/push seluruh folder | `/sync` hanya status; `/sync push` opt-in untuk commit yang sudah dibuat manusia |
| Search utama memakai database yang mungkin kedaluwarsa | CLI dan Telegram baru memakai Markdown terbaru; hybrid lama tersedia lewat tool terpisah |
| URL di-fetch untuk judul | URL dan catatan disimpan sebagai source; fetch halaman tidak dilakukan otomatis |
| Jurnal di folder umum | `/journal` baru menyimpan di `wiki/private/projects/`; jurnal lama tidak dipindah |
| `/read` mengambil kecocokan pertama | Path penuh atau kecocokan unik; jika ambigu, tampilkan pilihan |
| File audio/dokumen bisa bertabrakan nama | Nama unik; filename dari Telegram tidak menjadi path filesystem |
| Voice gagal dapat tetap berisi placeholder transkripsi | Audio asli disimpan; teks transkripsi hanya dibuat saat provider berhasil |
| Sintesis baru bercampur di root wiki | Runner baru menyimpan sumber/sintesis ke subdomain; provenance dan metadata konsisten |

`/ingest` v2 memproses paling banyak 10 file Markdown per panggilan dari `raw/` dan `inbox_raw/`, membuat source note, dan mengarsipkan sumber asli. Output menggunakan identitas berbasis isi/path sehingga kegagalan pemindahan dapat dilanjutkan tanpa memanggil AI ulang. Teks input panjang dipotong untuk konteks model; sumber lengkap tetap disimpan. Profil CRM otomatis hanya dibuat jika hasil terstruktur memuat nama dan kutipan bukti yang benar-benar ada pada sumber; fakta peran/organisasi yang tidak ada dalam kutipan diabaikan. `/crm` tetap tersedia untuk input manual.

Voice memakai local Whisper jika `LOCAL_WHISPER_MODEL` menunjuk file model yang sudah tersedia dan library `whisper` terpasang, lalu Groq Whisper, OpenAI Whisper, dan Gemini sesuai key yang dikonfigurasi. Dependency local Whisper tidak menjadi dependency core; tidak ada unduhan model otomatis oleh runner baru.

Layanan cloud hanya digunakan saat fitur yang memerlukannya dipanggil. Private notes dikecualikan dari konteks Q&A/sintesis cloud baru. `SECOND_BRAIN_INCLUDE_PRIVATE=1` hanya mengizinkan baca/status/search lokal/Telegram untuk pemilik, bukan memasukkan private ke analisis domain lain. Raw capture yang sensitif tetapi tidak diberi domain private tidak dapat dikenali otomatis.

Dokumen biner disimpan utuh; ekstraksi PDF/Word otomatis belum menjadi fitur core. Untuk source Markdown, gunakan `/ingest`. Scheduled jobs lama dan skrip eksperimen lama tetap memiliki perilakunya sendiri: review cron dan arahkan ke runner baru sebelum menganggapnya sudah bermigrasi.

Tidak ada migrasi database yang menghapus indeks lama. Ledger baru berada di `data/telegram-state.sqlite`; jangan hapus ledger untuk 'memperbaiki' pesan gagal karena itu bisa mengulang efek samping. Periksa artefak hasil, audit, dan pesan Telegram sebelum mengirim ulang perintah secara manual.

## Status verifikasi

Core dan compatibility entry points diuji lokal dengan fixture dan transport/provider mock. Tidak ada pesan Telegram live, panggilan AI berbayar, push GitHub, restart service VPS, atau migrasi cron yang dilakukan oleh pekerjaan lokal ini. `bot --check` hanya memvalidasi struktur konfigurasi, bukan keabsahan token/model.

Referensi protokol: [Telegram Bot API](https://core.telegram.org/bots/api), [Gemini text generation](https://ai.google.dev/gemini-api/docs/text-generation), [OpenAI file transcription](https://developers.openai.com/api/docs/guides/speech-to-text).
