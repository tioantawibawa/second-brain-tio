---
title: "Evaluasi Prompt Caching dan Context Window Compression"
source_url: "https://anthropic.com/research/prompt-caching"
author: "Amanda Askell"
ingest_date: 2026-09-27
---

Konsep penting:
Prompt caching memungkinkan penyimpanan prefix context statis di memory GPU, mengurangi latensi TTFT (Time to First Token) hingga 80% dan biaya inference token hingga 90%.
Sangat penting untuk arsitektur autonomous agent dengan system prompt besar dan RAG multi-turn.

Entitas penting:
- Prompt Caching
- TTFT Optimization
- Amanda Askell
- GPU VRAM Memory Pinning

Action items:
- Ukur penghematan biaya pada prompt berukuran > 10k token
- Terapkan cache control breakpoint pada layer agent orchestrator
