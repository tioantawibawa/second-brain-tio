---
title: Telegram Latency Anomaly Alerting System
slug: telegram-latency-anomaly-alerting-system
stream: core_work
target_folder: in_motion/core_work
type: in_motion
status: active
tags:
  - observability
  - telegram-bot
  - latency-monitoring
  - alerting
created_at: 2026-09-28
---

# Telegram Latency Anomaly Alerting System

## Overview
Sistem otomatisasi untuk mengirimkan *alert* via Telegram ketika terdeteksi latensi sistem melebihi threshold kritis (> 1500ms).

## Core Insights
- Deteksi anomali latensi real-time > 1500ms sangat krusial untuk menjaga SLA sistem production.
- Integrasi Telegram Webhook / Bot API menyediakan jalur eskalasi insiden yang instan bagi on-call engineer.
- Threshold 1500ms harus divalidasi terhadap baseline persentil p95 untuk menghindari alert fatigue.

## Key Entities
- [[telegram-bot-api]]
- [[latency-monitor]]
- [[anomaly-detection]]

## Action Items
- [ ] Setup Telegram Bot via BotFather dan dapatkan API token serta chat ID tujuan
- [ ] Implementasikan middleware/interceptors untuk tracking latensi request > 1500ms
- [ ] Buat script pengiriman HTTP POST ke Telegram Bot API saat anomali terdeteksi
- [ ] Lakukan testing load simulation untuk memicu alert dan verifikasi payload
