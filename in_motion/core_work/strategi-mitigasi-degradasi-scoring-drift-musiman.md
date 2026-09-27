---
title: "Strategi Mitigasi Degradasi Performa Model Scoring Akibat Drift Musiman"
slug: "strategi-mitigasi-scoring-drift-musiman"
stream: "core_work"
target_folder: "in_motion/core_work"
type: "in_motion"
status: "active"
tags:
  - "mlops"
  - "model-drift"
  - "scoring-engine"
  - "data-pipeline"
  - "feature-store"
---

# Strategi Mitigasi Degradasi Performa Model Scoring Akibat Drift Musiman

## 1. Executive Summary
Degradasi performa pada model scoring akibat pergeseran data musiman (seasonal shift) memerlukan pendekatan arsitektural yang proaktif. Dokumen ini merangkum strategi deployment dan monitoring untuk mendeteksi serta mengatasi *concept drift* dan *data drift* secara real-time.

## 2. Core Framework & Metrik Evaluasi
| Komponen | Metode / Tools | Threshold / Trigger | Action Plan |
| :--- | :--- | :--- | :--- |
| **Drift Detection** | Population Stability Index (PSI), Wasserstein Distance | PSI > 0.25 (Significant Drift) | Trigger automated alert ke on-call MLOps engineer |
| **Model Validation** | [[eval-harness-v1]], Out-of-Time (OOT) Validation | Drop AUC > 5% dari baseline | Switch ke fallback rule-based / shadow model |
| **Feature Store** | Real-time Feature Computation | Latency > 150ms | Scale up cluster resource / optimize query plan |

## 3. Action Items
- [ ] Implementasikan automated monitoring untuk PSI dan Jensen-Shannon Divergence pada top 20 features.
- [ ] Setup dynamic weighting ensemble antara baseline model dan seasonal-adjusted model.
- [ ] Validasi retrain trigger threshold menggunakan automated CI/CD pipeline untuk MLOps.