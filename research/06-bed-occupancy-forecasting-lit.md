# 06 — Bed Occupancy Forecasting: Academic Literature

## TL;DR
1. **LSTM/RNN models achieve ~6% MAPE on ward-level occupancy** — the accuracy is solved-problem territory in high-resource settings with EHR data; the hard part is getting training data, not the model.
2. **Length-of-Stay (LOS) prediction is the linchpin** — most bed-demand forecasting works by predicting discharge timing per patient, then aggregating to ward-level counts; without LOS you can't forecast.
3. **India-specific work is almost entirely COVID-era demand projections, not operational bed management** — the gap between what's been published globally and what exists for Indian hospitals is massive.

> **★ INSIGHT (Killing Feature A — predictor)** — The model isn't the moat; ground truth is. Our voice-verifier acts as a continual ground-truth source, calibrating a synthetic-data-trained predictor against real Yes/No/N-beds answers from a small sample of hospitals. That feedback loop is the differentiator that compensates for India's missing EHR census data.

---

## Best Approaches (What Works)

### Time-Series Models (ward/room level)
- **LSTM** trained on hourly aggregated individual bed data → predicts Bed Occupancy Rate (BOR) per ward and room
- Study: PMC10995785 (2024) — single-center retrospective cohort, LSTM outperformed ARIMA for intra-day patterns
- **RNNs**: MAPE of **6.24%** reported in mental-health-facility context (PMC11750970, 2025)

### Patient-Flow / Demand Forecasting
- **patientflow** (Python package, NHS-origin): real-time short-term predictions using snapshots of current inpatients + expected arrivals; converts patient-level LOS predictions into ward-level bed counts
- ResearchGate 2025 paper: ML models predicting daily bed demand — random forest and gradient boosting outperformed linear baselines
- Microsoft Fabric architecture: combines real-time sensor feeds + EHR + historical discharge patterns

### Hybrid AI approaches (2025)
- IAENG paper (IJCS_53_2): integrated LOS forecasting + NHP (Number of Hospitalized Patients) model → ward-specific demand curves
- Patent WO2025116287A1: ML occupancy model trained on time-dependent room-state transitions

---

## Key Features That Matter

**Strongest predictors (from literature):**
1. **Current census** (beds occupied right now) — strongest short-term signal
2. **Day of week + time of day** — discharge timing is highly cyclical
3. **LOS so far per patient** — hazard-model approach for discharge probability
4. **Admission type** (elective vs emergency) — elective has schedulable LOS, emergency doesn't
5. **Diagnosis/DRG** — LOS varies enormously by condition
6. **Seasonal/epidemiological signals** — flu season, monsoon patterns in India

**What doesn't add much:** Demographics alone, historical averages without recency weighting.

---

## Forecasting Horizons

| Horizon | Best method | Typical accuracy |
|---------|------------|-----------------|
| 0–6 hours | Census snapshot + LOS hazard | MAPE ~3–5% |
| 6–24 hours | LSTM on hourly census | MAPE ~6% |
| 1–7 days | Admission forecasting + LOS | MAPE ~10–15% |
| >7 days | Macro demand models | Rough estimates only |

---

## Low-Resource / India Context

**What exists:**
- COVID demand-supply gap projection (medrxiv 2020) — SEIR model for hospital surge, not operational tool
- St. John's Bangalore: patient load forecasting for COVID hospitals in Jalna (Maharashtra) and Simdega (Jharkhand) — ~1 month ahead predictions
- Mercatus Center report: explicitly notes **no central database tracks total private hospital bed capacity** in India

**The gap:**
- All operational bed-management ML work (LSTM, patientflow, etc.) assumes structured EHR data with per-patient timestamps — rare in Indian public hospitals
- Most Indian hospitals run paper records or fragmented EMRs; real-time census data doesn't exist at ward level in most facilities
- No published dataset of Indian hospital bed occupancy time-series exists publicly

---

## What to Build (Hackathon Recommendations)

1. **Use LOS-based forecasting as core primitive** — even coarse LOS estimates per ward type (medical/surgical/ICU) enable useful 24h forecasts
2. **Synthetic data is acceptable** — generate realistic occupancy patterns from distributions calibrated to Indian public hospital statistics (NHM data)
3. **Short-term (6–24h) is the highest-value window** — matches the "will this patient need a bed tomorrow" clinical question
4. **patientflow library** is the most hackable open-source starting point
5. **Don't need per-patient EHR** — ward-level census snapshots (even manual entry every 4h) are enough to bootstrap an LSTM

> **★ INSIGHT (architecture)** — `patientflow` (NHS-origin, Python) is the most hackable open-source starting point. Wrap as a UC function, register the trained model in MLflow, serve via Models-from-Code. This pattern matches the Care Cost Compass reference (research/08) judges already know.

---

## Sources
- https://pmc.ncbi.nlm.nih.gov/articles/PMC10995785/ (LSTM ward BOR prediction, 2024)
- https://pmc.ncbi.nlm.nih.gov/articles/PMC11750970/ (RNN mental health beds, MAPE 6.24%, 2025)
- https://www.researchgate.net/publication/391584272 (ML daily bed demand, 2025)
- https://atlas.hsma.co.uk/packages_projects_tools/patientflow/patientflow.html (patientflow package)
- https://www.iaeng.org/IJCS/issues_v53/issue_2/IJCS_53_2_29.pdf (AI forecasting hospital bed capacity)
- https://www.medrxiv.org/content/10.1101/2020.05.14.20100537v1 (India COVID demand-supply)
- https://www.stjohns.in/research-institute/publications/modelling-and-forecasting-capacity-needs (India hospital forecasting)
- https://www.mercatus.org/system/files/rajagopalan-india-healthcare-mercatus-v2.pdf
- https://learn.microsoft.com/en-us/fabric/real-time-intelligence/architectures/hospital-operations
- https://patents.google.com/patent/WO2025116287A1/en
