---
title: "AI Agent Pencari dan Penguji Coupon Promo Indonesia"
slug: "ai-agent-coupon-promo-indonesia"
stream: "side_builder"
target_folder: "in_motion/side_builder"
type: "in_motion"
status: "incubating"
tags:
  - "ai-agent"
  - "coupon-finder"
  - "automation"
  - "ecommerce"
  - "indonesia"
created_at: "2026-09-27"
---

# AI Agent Pencari dan Penguji Coupon Promo Indonesia

## Overview
Pengembangan AI Agent mandiri yang bertugas melakukan aggregrasi, pencarian, dan automated testing terhadap kode kupon/promo untuk berbagai produk dan platform e-commerce di Indonesia.

## Core Architecture
| Component | Technology | Function |
| :--- | :--- | :--- |
| **Scraper Agent** | Python, BeautifulSoup, Serper API | Scraping kode promo dari aggregator & social media |
| **Validation Agent** | Playwright, Headless Chrome | Automated testing langsung ke cart/checkout e-commerce |
| **Orchestrator** | LangChain / CrewAI | Mengatur flow dari discovery hingga verification |

## Action Items
- [ ] Definisikan scope target e-commerce dan merchant di Indonesia
- [ ] Rancang arsitektur agent menggunakan framework seperti LangChain atau CrewAI
- [ ] Implementasikan module scraping untuk agregasi kode promo dari berbagai source
- [ ] Bangun test execution engine menggunakan Playwright/Selenium untuk validasi otomatis
- [ ] Setup deployment pipeline untuk MVP

## References
- [[coupon-agent-v1]]
- [[headless-browser-automation]]
- [[ecommerce-validator]]