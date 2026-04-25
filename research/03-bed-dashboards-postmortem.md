# 03 — Why State Bed Dashboards Decayed (2020–2025 Postmortem)

## TL;DR

1. **CAG audits revealed "phantom beds":** 2024 Punjab CAG audit found Tocilizumab in **294-day stockout**, $500k+ liquid oxygen tanks **lying unconnected to pipelines** at GMCH Ambikapur / DKS PGI Raipur / GMCH Jagdalpur, and only **4 of 11 critical drugs** consistently available. Dashboards showed beds "available"; patients were turned away at the door.
2. **Universal failure mode = human-in-the-loop latency:** all 8 state dashboards collapsed for the same reason — single nodal officers managing 1,500+ patients while typing into a web form. Data lagged 12+ hours during peak Delta. Dashboards actively misdirected ambulances.
3. **By 2024–2025 every dashboard is dead, stale, or repurposed.** BMC announced a full rebuild from scratch in 2025. Telangana URLs are dead. Kerala gracefully retired hers. **Despite ₹23,123 crore sanctioned under ECRP-II, no state has a working public bed feed in 2025.**

> **★ INSIGHT (Killing Feature A core thesis)** — The "ghost bed" failure is *the* reason our pitch starts with prediction + voice verification. Real-time dashboards have been tried, funded, and audited to death. Repeating that approach loses; differentiating from it wins.

---

## State-by-State Decay Matrix

| State / URL | Owner | Status (2024–25) | Failure mode |
|---|---|---|---|
| **Delhi** `corona.delhi.gov.in` | Dept of Health & FW | Stale — fields blank | Phantom beds: tracked mattresses, not staff/oxygen |
| **Tamil Nadu** `stopcorona.tn.gov.in` | NHM + State DoH | Repurposed (env/health) | Coerced private hospital listings without consent → patients rejected at door |
| **Maharashtra** `mcgm.gov.in` (BMC) | BMC | Dead — 2025 rebuild announced | One nodal officer per 1,500 patients; manual updates collapsed |
| **Karnataka** `chbms.bbmpgov.in` (BBMP) | BBMP | Glitchy / inactive | API crashes, obsolete frameworks, no algorithmic queue → VIP bed-blocking |
| **Gujarat** `gujcovid19.gujarat.gov.in` | State Govt | Stale | No private-hospital API, urban/rural fragmentation |
| **West Bengal** `wb.gov.in/COVID-19` | WBMSC | Defunct | Strategic pivot to physical Critical Care Blocks (50–100 beds × 9 colleges) |
| **Kerala** `covid19jagratha.kerala.nic.in` | Kerala IT Mission | Repurposed (general health) | Worked initially (75% digital literacy), retired as Omicron defanged demand |
| **Telangana** `covid19.telangana.gov.in` | District Admin / NIC | Dead links | IVRS + PDF bulletins, no API integration. Bypassed via Twitter helplines |

---

## CAG Findings (The Damning Numbers)

### Punjab (2024 Performance Audit)
- **Bed deficits up to 100%** vs IPHS norms in test-checked facilities
- **GMCH Patiala, designated COVID hospital:**
  - 11 prescribed drugs critical for COVID care — only **4 consistently available**
  - Stockouts: Remdesivir, antimicrobials, Enoxaparin, **Tocilizumab (294 days)**
- **Liquid Medical Oxygen tanks idle, unconnected to pipelines** at GMCH Ambikapur, DKS PGI Raipur, GMCH Jagdalpur

### Haryana (2024 Performance Audit)
- "State Government had not made district-wise plan detailing the status of bed availability"
- CHCs/PHCs below IPHS 2012 minimums
- Tender for Health Institutions mapping awarded only **Feb 2023** — i.e. real-time tracking did not exist during the actual crisis

> **★ INSIGHT (Killing Feature A — clinical readiness)** — A bed without oxygen/drugs/staff isn't a bed. Our prediction + voice layer must verify *clinical readiness*, not bed count. The "Cost-Truth Advisor" idea (medical + non-medical cost on each recommendation) maps directly to what families actually care about: will the bed actually accept us, or will we travel for nothing?

---

## Failure Modes Ranked

### #1. Human-in-the-Loop Latency (universal)
Single nodal officers, 1,500+ patients, manual web form updates. Data lagged hours-to-days during surges. **A 12-hour-stale dashboard is worse than no dashboard** — it actively misroutes ambulances.

### #2. Phantom Beds (Punjab/Haryana CAG, Delhi)
Backend never correlated bed status with oxygen pressure, drug inventory, or staff rosters. "Available" was mathematically true, clinically false.

### #3. Coerced Private-Sector Listings (Tamil Nadu)
States listed private hospitals on dashboards without consent. Hospitals (e.g. Theni district: Krishnamaal Memorial, NRT, TNKHNV — 60 beds, 18 oxygen, 23 ICU, 7 ventilators *on paper*) had no isolation infrastructure and rejected arrivals.

### #4. API/Server Fragility, Zero EMR Integration (Karnataka CHBMS)
Monolithic apps on obsolete frameworks. Crashes during peak load showed "Blank" across ICU/ventilator categories. Government dashboards never integrated with hospital EMR/admission systems.

### #5. No Algorithmic Triage / Queuing (Bengaluru)
Broadcast availability without booking. "Run on the bank" effect — multiple ambulances converged on one facility. VIP back-channels bypassed the system entirely.

### #6. No Endemic Pivot (universal)
Single-purpose emergency tools. When Omicron/JN.1 reduced ICU demand, no architectural flexibility to repurpose for elective beds, OPD slots, or routine ER triage. Abandonment followed.

---

## What 2024–2025 ML/IoT Literature Says Works

- **BiLSTM forecasting weekly bed occupancy:** 98.06% accuracy, MAPE 1.939%, fluctuation ±13 beds (mental-health hospital, 2025)
- **MLP-Ridge classifier (Chennai 2025):** 91% accuracy, MCC 82% for case-demand-driven facility expansion
- **Hemodynamic alerting (multicenter 2025):** 79.2% sensitivity, 80.1% specificity, 68.7% PPV — IoT continuous monitoring beats manual nodal-officer reports
- **AIG Hospitals Hyderabad (private, 620-bed, web-based BMS):** occupancy 75% → 80%, monthly admissions +12%, bed turnover +11% — **integrated dashboards work; external reporting chores don't**

> **★ INSIGHT (Killing Feature A architecture)** — The literature has solved the algorithm. The unsolved problem in India is *getting calibrated training/ground-truth data*. Our voice-verifier feeding back into the predictor is exactly the missing primitive — it generates ground truth on the fly without burdening hospital staff.

---

## Strategic Implications for a Differentiated System

1. **Eliminate human-in-the-loop reporting.** No nodal officer typing into a form. Either webhook from existing HIS, or *infer* from predictor + voice spot-checks.
2. **Track clinical readiness, not physical beds.** Correlate with oxygen pressure (IoT), pharmacy ERP, staff rosters. If we can't measure those, we publish a *probability* with confidence bands — never claim "available."
3. **Predictive forecasting + algorithmic queuing.** BiLSTM / patientflow-style for the predictor. Auditable digital queue (no VIP bypass) for allocation. ML evaluation panel (MLflow drift) on stage = the Databricks-judge wow moment.

---

## Sources
- CAG Performance Audit reports — Punjab, Haryana (tabled 2024)
- IJCMph 2024 (quality of care vs occupancy)
- JCM 2025 (dashboard decay)
- BMC 2025 relaunch directives (Mumbai)
- BiLSTM mental-health bed forecasting study, 2025
- MLP-Ridge Chennai dashboard study, 2025
- AIG Hospitals Hyderabad bed-management case study
- BMJ Global Health / ResearchGate (Kerala)
- PRS India audits (Telangana)
