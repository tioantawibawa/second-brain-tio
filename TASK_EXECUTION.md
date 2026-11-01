# Task eksekusi: ide → dua agen → review → Codex

Alur ini menyiapkan ide menjadi rencana yang bisa ditinjau sebelum dikerjakan.

| Peran | Tanggung jawab | Keluaran |
| --- | --- | --- |
| Agen 1 | Ekstrapolasi ide menjadi tugas konkret, urutan, dependensi, dan kriteria selesai | `01-tasks.md` |
| Agen 2 | Review breakdown dan susun framework proposal, rekomendasi skill, dan prompt Codex | `02-proposal.md` dan `04-execution-prompt.md` |
| Tio | Review lingkup, asumsi, dan pilihan pendekatan | Setujui lingkup tertentu, revisi, atau tunda |

Nama file sebenarnya memakai awalan ID unik agar beberapa ide tidak saling menimpa. Agen berjalan berurutan karena proposal membutuhkan breakdown Agen 1.

## Cara menggunakan

Klik dua kali `brain.cmd`, pilih **6. Task eksekusi**, tulis ide dan pilih domain. Atau jalankan:

```powershell
.\brain.cmd plan "Buat proses monitoring drift scoring bulanan" --domain work
.\brain.cmd plan --file "C:\catatan\ide.txt" --title "Ide dashboard" --domain engineering
```

Perintah itu **menyiapkan dokumen dan prompt**, tanpa memanggil model AI. Terminal langsung menampilkan prompt orkestrasi yang bisa disalin. Prompt yang sama tersimpan di dokumen `03-codex-prompt`.

1. Salin prompt orkestrasi tersebut ke Codex. Prompt sudah mengizinkan dua subagent untuk tahap perencanaan. Jika subagent tidak tersedia, dua peran dijalankan berurutan dengan keterangan yang jelas.
2. Agen 1 menulis breakdown. Agen 2 menerima hasilnya dan menyusun proposal serta prompt eksekusi berdasarkan konteks yang tersedia.
3. Review proposal. Contoh keputusan: “Setujui proposal versi 1 untuk T01–T03” atau “Revisi: batasi ke prototipe lokal”.
4. Salin prompt final dari `04-execution-prompt` ke Codex. Jika chat baru belum memiliki keputusan review, Tio mengetik langsung persetujuan lingkup yang sama. Kutipan dari dokumen atau kalimat persetujuan buatan agen tidak dianggap keputusan Tio. Prompt mengecek persetujuan tersebut sebelum implementasi.

Tidak ada ide asli yang diberikan sebagai contoh di sini. Perintah contoh tidak dijalankan ke vault pengguna. Paket awal mengandung format kosong berlabel pending; analisis baru dihasilkan saat prompt dijalankan di Codex.

## Lokasi dokumen dan status

Paket disimpan di `wiki/<domain>/projects/`:

- `<id>-00-brief.md`: ide asli, konteks, dan tautan antar-artifact.
- `<id>-01-tasks.md`: tugas Agen 1.
- `<id>-02-proposal.md`: proposal Agen 2 untuk review.
- `<id>-03-codex-prompt.md`: prompt orkestrasi yang langsung dapat disalin.
- `<id>-04-execution-prompt.md`: prompt yang diisi Agen 2 setelah analisis.

`status: incubating` membedakan perencanaan dari pekerjaan yang sudah aktif. `review_status` berubah dari `pending` menjadi `ready_for_review` setelah dua peran selesai. Persetujuan perlu menunjuk versi proposal dan task/lingkup yang jelas; file template tidak memberi persetujuan. HOME menampilkan tautan paket non-private dan diperbarui saat paket dibuat.

Pilih domain `private` untuk ide pribadi. Paket private disimpan di `wiki/private/projects/` dan tidak ditautkan pada HOME atau dibuka detailnya pada audit log umum. Penamaan domain work/engineering tidak otomatis mendeteksi seluruh data sensitif; pilih domain sesuai isi ide.

## Skill yang disediakan

Skill lokal: `.agents/skills/second-brain-execution/SKILL.md`, dengan referensi terpisah untuk masing-masing agen. Buka proyek Second Brain di Codex untuk bekerja dengan konteks lokalnya. Prompt juga menyertakan path skill secara eksplisit, sehingga instruksinya tetap bisa dibaca jika belum muncul di katalog chat yang sedang terbuka.

Skill tambahan dipilih Agen 2 sesuai pekerjaan dan yang tersedia pada sesi tersebut. Tidak ada pemasangan otomatis atau klaim bahwa skill tertentu pasti tersedia di semua proyek. Struktur skill mengikuti [dokumentasi resmi OpenAI](https://learn.chatgpt.com/docs/build-skills).
