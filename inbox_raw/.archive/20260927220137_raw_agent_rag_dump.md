Ide build agent baru untuk verifikasi RAG otomatis di pipeline staging.
Problem: LLM hallucination sering lolos ke client deliverable di enterprise core work, butuh automated evaluator agent yang jalan independen sebagai side builder service.

Arsitektur yang direncanakan:
- FastAPI microservice di VPS
- Gemini 3.8 Flash untuk semantic judge dengan temperature 0.0
- SQLite / Chroma untuk test fixture
- Target p95 latency < 350ms, evaluasi batch 50 dokumen < 10 detik

Actions yang harus segera dieksekusi:
- [ ] Buat evaluator harness script dengan Python
- [ ] Set API endpoint POST /v1/eval/rag
- [ ] Setup systemd unit service di VPS
- [ ] Integrasikan webhook trigger ke GitHub Actions CI

Koneksi konsep:
Butuh merujuk ke [[eval-harness-v1]] dan [[latency-optimization-playbook]].
