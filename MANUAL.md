# Manual Second Brain v3

Mulai dari [QUICKSTART.md](QUICKSTART.md). Antarmuka utama adalah Telegram bertombol dan dashboard lokal melalui **brain.cmd**.

- Data, reset, dan perbedaan versi: [MIGRATION_V3.md](docs/MIGRATION_V3.md).
- Proposal, dua peran AI, review, dan prompt: [TASK_EXECUTION.md](TASK_EXECUTION.md).
- Push kode, migrasi service, dashboard melalui tunnel dan rollback: [DEPLOYMENT_V3.md](docs/DEPLOYMENT_V3.md).

Core memerlukan Python 3.10+ tanpa paket tambahan. Pertahankan `.env` yang valid dan tentukan model yang tersedia pada akun. Capture/task/search dapat dipakai tanpa AI. Menjalankan provider cloud mengikuti kuota/biaya akun; mock tests tidak menguji provider live.

Reset mengarsipkan konten aktif dan memilih workspace baru. Tidak ada penghapusan permanen, publikasi, git push, atau reset ledger Telegram otomatis. `.brain/` adalah data privat; cadangkan terpisah dari kode. Root legacy tidak lagi menjadi sumber utama setelah reset.
