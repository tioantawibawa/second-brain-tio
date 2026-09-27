---
title: "Evaluasi Prompt Caching dan Context Window Compression"
source_title: "test-prompt-engineering.md"
source_url: "https://anthropic.com/research/prompt-caching"
author: "Amanda Askell"
ingest_date: 2026-09-27
tags:
  - wiki
  - knowledge-compilation
links:
  - "[[raw/processed/test-prompt-engineering.md]]"
  - "[[crm/Amanda-Askell|Amanda Askell]]"
  - "[[Prompt Caching]]"
  - "[[TTFT Optimization]]"
  - "[[GPU VRAM Memory Pinning]]"
---

# Evaluasi Prompt Caching dan Context Window Compression

## 1. Core Synthesis & Key Insights
- Prompt caching menyimpan prefix context statis di GPU memory, mereduksi TTFT (Time to First Token) hingga 80%.
- Efisiensi biaya inference token mencapai 90%, sangat krusial untuk autonomous agent dengan system prompt besar dan multi-turn RAG.

---

## 2. Tools, Arsitektur & Entitas
| Entitas / Tool | Tipe | Relevansi |
| :--- | :--- | :--- |
| [[crm/Amanda-Askell|Amanda Askell]] | Personal CRM | Referensi silang |
| [[Prompt Caching]] | Wiki Concept | Referensi silang |
| [[TTFT Optimization]] | Wiki Concept | Referensi silang |
| [[GPU VRAM Memory Pinning]] | Wiki Concept | Referensi silang |

---

## 3. Actionable Takeaways
- [ ] Ukur penghematan biaya pada prompt berukuran > 10k token
- [ ] Terapkan cache control breakpoint pada layer agent orchestrator

---

## 4. Provenance & Original Source Reference
- File Asli: `[[raw/processed/test-prompt-engineering.md]]`
- Waktu Ingest: `2026-09-27 23:43`
