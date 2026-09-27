---
title: "LLM & Microservice Latency Optimization Playbook"
id: "latency-optimization-playbook"
type: lattice
stream: meta_system
status: evergreen
created_at: 2026-09-27
updated_at: 2026-09-27
tags:
  - latency
  - performance
  - fastapi
links:
  - "[[eval-harness-v1]]"
---

# LLM & Microservice Latency Optimization Playbook

## 1. Core Thesis
Optimasi latensi pada sistem berbasis LLM agent harus menargetkan dua domain: latensi jaringan (I/O) dan waktu pembentukan konteks (*token prefill & streaming*).

---

## 2. Standard Optimization Checklist

| Layer | Intervensi | Ekspektasi Penurunan Latensi |
| :--- | :--- | :--- |
| **Model Selection** | Beralih ke model flash/nano untuk step klasifikasi | $-60\%$ TTFT |
| **Connection Pool** | HTTP keep-alive & persistent connection pooling | $-100\text{ms}$ per hop |
| **Streaming** | Server-Sent Events (SSE) untuk deliverable interaktif | Instant perceived response |
| **Prompt Pruning** | Minimalkan contoh zero-shot/few-shot yang redundant | $-25\%$ prefill cost |

---

## 3. Rules of Thumb
- Ukur p95 dan p99, jangan hanya melihat rata-rata (mean).
- Cache embedding statis menggunakan in-memory cache sebelum menyentuh vector store.
