---
title: "Raw Agent Rag Dump"
id: "20260927-raw-agent-rag-dump"
type: in_motion
stream: core_work
status: active
created_at: 2026-09-27
updated_at: 2026-09-27
tags:
  - core-work
  - second-brain-ingest
links:
  - "[[agent-playbook]]"
  - "[[fastapi-playbook]]"
  - "[[gemini-playbook]]"
  - "[[git-playbook]]"
  - "[[python-playbook]]"
  - "[[rag-playbook]]"
  - "[[vps-playbook]]"
---

# Raw Agent Rag Dump

## 1. Executive Summary & Core Insights
- Inisiatif Raw Agent Rag Dump berorientasi langsung pada implementasi teknis dan output terukur.
- Komponen modular siap diintegrasikan dengan arsitektur sistem yang ada.
- Ide build agent baru untuk verifikasi RAG otomatis di pipeline staging.

---

## 2. Key Entities & Knowledge Connections
| Entitas / Modul | Kategori | Relasi Sistem |
| :--- | :--- | :--- |
| [[agent-playbook]] | Knowledge Lattice | Fondasi arsitektur pendukung |
| [[fastapi-playbook]] | Knowledge Lattice | Fondasi arsitektur pendukung |
| [[gemini-playbook]] | Knowledge Lattice | Fondasi arsitektur pendukung |
| [[git-playbook]] | Knowledge Lattice | Fondasi arsitektur pendukung |
| [[python-playbook]] | Knowledge Lattice | Fondasi arsitektur pendukung |
| [[rag-playbook]] | Knowledge Lattice | Fondasi arsitektur pendukung |
| [[vps-playbook]] | Knowledge Lattice | Fondasi arsitektur pendukung |

---

## 3. Action Items & Execution Triggers
- [ ] Buat evaluator harness script dengan Python
- [ ] Set API endpoint POST /v1/eval/rag
- [ ] Setup systemd unit service di VPS
- [ ] Integrasikan webhook trigger ke GitHub Actions CI

---

## 4. Raw Dump Context & Original Notes
```text
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
```
