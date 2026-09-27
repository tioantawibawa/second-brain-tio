---
title: "War Room Pre-Mortem: Menetapkan harga proyek migrasi AI secara Fixed-Price"
type: war_room_pre_mortem
status: active
decision_target: "Menetapkan harga proyek migrasi AI secara Fixed-Price"
created_at: 2026-09-28
tags:
  - war-room
  - pre-mortem
  - red-team
  - decision-strategy
  - risk-mitigation
links:
  - "[[index]]"
  - "[[RULES]]"
---

# War Room Pre-Mortem: Menetapkan harga proyek migrasi AI secara Fixed-Price

> **Simulasi Red Team Adversary & Stress-Testing Keputusan**  
> Dihasilkan secara otonom melalui **PROTOKOL 6: OPERASI WAR ROOM PRE-MORTEM**  
> Tanggal Analisis: `2026-09-28`

---

## 1. Tesis Retrospektif (Kilas Balik Kegagalan dari Masa Depan)

Proyek migrasi AI senilai Rp 150 juta ini berubah menjadi bencana finansial dan operasional akibat jebakan fixed-price yang mengasumsikan sistem AI deterministik layaknya software konvensional. Di tengah tingginya konkurensi tugas dan beban kognitif pengembang yang kerap melupakan komitmen rapat, proyek ini tersandung oleh 'moving goalposts' dari klien, instabilitas non-deterministik LLM, serta penalti denda keterlambatan yang menggerus seluruh margin profit dalam hitungan minggu.

---

## 2. Failure Modes (3 Skenario Kegagalan Paling Realistis)

### Skenario 1: Prompt Engineering & Evaluation Infinite Loop (`Probabilitas: Kritis`)
- **Rantai Kausalitas (Mechanism)**:  
  Model AI gagal mencapai target akurasi yang dijanjikan dalam kontrak fixed-price karena data produksi klien kotor atau berubah-ubah. Tim terjerumus dalam siklus eksperimen prompt caching, fine-tuning, dan modifikasi graph orchestration yang memakan waktu berlipat-lipat tanpa tambahan pendapatan.
- **Leading Indicator / Trigger Event**:  
  > [!WARNING] Tanda Bahaya Awal
  > Klien menolak hasil uji coba pertama karena akurasi output agentic workflow di bawah 90%, menuntut penyesuaian ulang cakupan prompt.

---

### Skenario 2: Latency Avalanche & SLA Penalty Trap (`Probabilitas: Tinggi`)
- **Rantai Kausalitas (Mechanism)**:  
  Arsitektur multi-agent yang kompleks mengalami latensi tinggi di luar batas wajar akibat overhead context window dan network hop. Karena terikat klausul penalti denda keterlambatan, setiap milidetik kelambatan di atas threshold 1500ms langsung memotong nilai kontrak bersih secara eksponensial.
- **Leading Indicator / Trigger Event**:  
  > [!WARNING] Tanda Bahaya Awal
  > Lonjakan latensi tak terduga saat token usage membludak, memicu alert Telegram otomatis yang mengonfirmasi bahwa denda harian mulai berjalan.

---

### Skenario 3: Cognitive Overflow & Scope Creep Blindness (`Probabilitas: Menengah`)
- **Rantai Kausalitas (Mechanism)**:  
  Pengembang mengalami kelelahan mental akibat menangani banyak lini paralel (high-concurrency builder) dan gagal mendokumentasikan permintaan tambahan klien dalam rapat. Perubahan kecil yang disetujui secara lisan menumpuk menjadi beban kerja masif yang melampaui estimasi awal fixed-price.
- **Leading Indicator / Trigger Event**:  
  > [!WARNING] Tanda Bahaya Awal
  > Klien mengklaim fitur ekstra (seperti alert anomali latensi otomatis) termasuk dalam ruang lingkup fixed-price, sementara pengembang lupa detail komitmen rapat sebelumnya.

---



## 3. Unstated Assumptions (Asumsi Terselubung vs Fakta Lapangan)

| No | Asumsi Terselubung | Mengapa Rapuh / Cacat | Reality Check & Batasan Riil |
| :--- | :--- | :--- | :--- |
| 1 | **Perilaku dan output sistem AI dapat diestimasi waktunya secara akurat seperti proyek pembuatan CRUD aplikasi web konvensional.** | AI bersifat non-deterministik; eksperimen prompt, penanganan halusinasi, dan debugging agen tidak memiliki kurva waktu yang linier. | `Debugging agen AI dan orkestrasi siklus sering kali memakan 80% waktu proyek hanya untuk memperbaiki 20% kasus edge-case yang tidak terduga.` |
| 2 | **Klien memiliki pemahaman teknis yang matang tentang batasan teknologi AI dan tidak akan mengubah ekspektasi di tengah jalan.** | Klien enterprise sering kali memperlakukan AI sebagai 'kotak hitam ajaib' yang bisa melakukan apa saja secara instan tanpa biaya tambahan. | `Scope creep tidak terelakkan karena klien terus meminta penambahan fitur agentic workflow baru setelah melihat prototipe awal.` |
| 3 | **Kapasitas kognitif tim cukup untuk mengawasi eksekusi proyek tanpa melewatkan detail komitmen kritis.** | Beban kerja paralel yang tinggi memicu kelupaan komitmen rapat dan hilangnya kontrol pelacakan proyek. | `Catatan quick capture menunjukkan riwayat rentan lupa komitmen rapat dan tingginya risiko cognitive overload.` |


---

## 4. Blindspot Questions (5 Pertanyaan Tajam yang Wajib Dijawab)

1. **Bagaimana kita mengukur batas akhir (stop-criteria) dari eksperimen prompt dan tuning sebelum merugi?**
2. **Klausul pembatas apa yang melindungi kita jika klien secara sepihak mengubah definisi 'sukses' migrasi AI?**
3. **Apakah kita memiliki mekanisme pencatatan rapat otomatis yang mengikat komitmen klien secara hukum untuk mencegah scope creep?**
4. **Berapa besar cadangan finansial yang harus disiapkan untuk menutupi potensi penalti denda keterlambatan?**
5. **Mengapa kita memilih model fixed-price padahal ketidakpastian teknis LLM dan arsitektur agentic berada di titik tertinggi?**


---

## 5. Actionable Mitigation & Circuit Breaker Protocol

### Mitigasi 1: Ubah skema kontrak dari Fixed-Price murni menjadi Time & Material dengan hard ceiling cap, atau Fixed-Price berfase ketat (milestone-based).
- **Mekanisme Guardrail**: Klausul adendum kontrak yang mewajibkan amandemen tertulis untuk setiap penambahan fitur atau perubahan data source.
- **Ambang Batas Kuantitatif (Kill-Switch Threshold)**:  
  > [!IMPORTANT] Threshold Batas Toleransi
  > `Scope variance > 5% dari dokumen spesifikasi awal wajib memicu negosiasi tagihan tambahan.`

---

### Mitigasi 2: Implementasikan Shadow Harness dan Automated Telemetry Monitoring untuk memantau performa agentic workflow secara real-time.
- **Mekanisme Guardrail**: Alert otomatis via Telegram jika latensi atau token cost melewati batas operasional yang disepakati.
- **Ambang Batas Kuantitatif (Kill-Switch Threshold)**:  
  > [!IMPORTANT] Threshold Batas Toleransi
  > `Latensi rata-rata > 1500ms atau error rate > 2% selama 3 hari berturut-turut.`

---

### Mitigasi 3: Terapkan protokol Identity Debugging dan transkrip rapat otomatis untuk mengeliminasi kelupaan komitmen proyek.
- **Mekanisme Guardrail**: Sistem verifikasi task harian yang menyinkronkan hasil rapat dengan backlog proyek secara sinkron.
- **Ambang Batas Kuantitatif (Kill-Switch Threshold)**:  
  > [!IMPORTANT] Threshold Batas Toleransi
  > `Zero unrecorded commitments dalam setiap akhir sesi meeting dengan klien.`

---



## 6. Grounding Vault & Audit Traceability

### A. Titik Stres & Bias Kognitif Masa Lalu (`journal/`)
- [[journal/quick_captures|quick_captures]]
- [[journal/2026-09-27_lupa-project-rapat|Mengatasi Kelupaan Komitmen Proyek dari Rapat]]

### B. Sounding Board & Jaringan Pakar Terkait (`crm/`)
- [[crm/Amanda-Askell|Amanda Askell]] (Subject Matter Expert / Author)
- [[crm/Harrison-Chase|Harrison Chase]] (Creator & Co-Founder / CEO)

### C. Referensi Teknis & Batasan Arsitektur (`wiki/` & `lattices/`)
- [[wiki/langgraph-multi-agent-orchestration-patterns|langgraph-multi-agent-orchestration-patterns]]
- [[wiki/analisis-implementasi-prompt-caching-agentic-rag|analisis-implementasi-prompt-caching-agentic-rag]]
- [[wiki/synthesis_credit-risk_tactical-football-analytics|synthesis_credit-risk_tactical-football-analytics]]
- [[wiki/hacker-news-signal-ingestion-setup|hacker-news-signal-ingestion-setup]]
- [[lattices/identity-debugging-walk-protocol|identity-debugging-walk-protocol]]
