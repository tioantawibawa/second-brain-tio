---
title: "Agent Evaluation Harness Architecture Pattern"
id: "eval-harness-v1"
type: lattice
stream: meta_system
status: evergreen
created_at: 2026-09-27
updated_at: 2026-09-27
tags:
  - evaluation
  - agentic-ai
  - architecture
links:
  - "[[latency-optimization-playbook]]"
---

# Agent Evaluation Harness Architecture Pattern

## 1. Core Thesis & Problem Space
Mengevaluasi LLM agent dalam pipeline produksi membutuhkan pemisahan ketat antara *generation runtime* dan *evaluation harness*. Tanpa evaluasi deterministik berbasis unit test kode dan semantic judging, regresi penalaran (*reasoning regression*) sulit dideteksi sebelum menyentuh klien.

---

## 2. Technical Blueprint

```mermaid
sequenceDiagram
    autonumber
    participant Runner as Test Runner
    participant Agent as Agent Under Test
    participant Sandbox as Execution Sandbox
    participant Judge as Gemini Evaluator (temp=0.0)

    Runner->>Agent: Send Benchmark Prompt
    Agent->>Sandbox: Execute Tool Call
    Sandbox-->>Agent: Tool Output
    Agent-->>Runner: Final Deliverable
    Runner->>Judge: Pass Output + Ground Truth
    Judge-->>Runner: Deterministic Score (Pass/Fail)
```

---

## 3. Rules of Thumb
1. **Determinism First**: Evaluasi sintaks dan status exit code selalu didahulukan sebelum evaluasi semantik dengan LLM.
2. **Batch Isolation**: Setiap skenario pengujian harus berjalan dalam sandbox terisolasi untuk menghindari state pollution.
3. **Budget Guard**: Batasi token generation maksimal per langkah evaluasi.
