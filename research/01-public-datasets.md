# 01 — Public Indian Hospital Datasets

## TL;DR
1. **NHRR captured 20 lakh+ establishments across 1400+ variables** — but it's a policy/planning database, not a live API; real-time occupancy data doesn't exist at national level.
2. **data.gov.in has state/UT-wise bed counts** — but the most granular Kaggle-sourced datasets are from July 2018; nothing current or real-time is publicly downloadable.
3. **A real-time national bed-tracking portal has been proposed in 2025 academic literature but doesn't exist yet** — the gap is documented, not filled.

> **★ INSIGHT (Killing Feature A)** — There is no national real-time bed feed to compete with, scrape, or copy. This is *why* prediction + spot-check voice verification beats dashboard rebuilds: nothing exists to reuse, and the previous attempts (research/03) all decayed.

---

## ABDM Health Facility Registry (HFR)

**What it is:** Core building block of ABDM — assigns unique identifiers to all healthcare facilities in India (public + private). Focus is on *registration and identity*, not on bed availability or occupancy.

**What it contains:**
- Facility name, type, location, contact
- Registered practitioners linked to the facility
- Unique Health Facility ID for ABDM interoperability

**How to access:** `facility.abdm.gov.in` — registration portal, not a data download API. There is an ABDM sandbox for developers but it provides identity/linking capabilities, not aggregate supply data.

**Limitations for hackathon:**
- No bed occupancy data
- No real-time capacity signals
- Useful only as a facility lookup / geocoding layer

---

## NHRR (National Health Resource Repository)

**What it is:** A government initiative under CBHI (Central Bureau of Health Intelligence) to map all healthcare resources — facilities, providers, diagnostics, pharmacies.

**What it contains:** 20 lakh+ establishments × 1400+ variables including bed counts, specialties, equipment, staff numbers.

**Access:** Primarily a policy/research tool. Data is not served as a live API — published in NHP reports and periodic CBHI publications.

**What's actually usable:**
- Aggregated state-level stats in National Health Profile (NHP) PDFs
- Mapped in Sage Journals academic study on Indian health data sources

**Limitations:** Snapshot data, not real-time. Private sector coverage is incomplete.

---

## data.gov.in

**Available datasets:**
- "State/UT-wise Number of Government Hospitals and Beds in Rural and Urban Areas" (provisional) — NHM data
- Ward-wise facility details (name, type, level, beds, doctors) for some states
- Vacancy data for doctors/nurses in central government hospitals

**Reality check:** Static CSV/Excel downloads. Most current files are 2-4 years old. No API, no real-time feed.

**Best Kaggle proxies:**
- `fringewidth/hospitals-in-india` — NIT Jalandhar + web scraping, anonymized
- `dheerajmpai/hospitals-and-beds-in-india` — state-wise, July 2018 snapshot

---

## State Portals

**COVID-era dashboards (2020–2021):** Several states built real-time bed dashboards during COVID (research/03 covers why most decayed after 2021). Maharashtra, Karnataka, Delhi had the most functional ones.

**Current state:** Most are either offline, stale, or behind login walls. No state has a publicly accessible live API for bed occupancy as of 2025.

**Proposed solution (2025):** A preprint (preprints.org, Sep 2025) explicitly argues for a "centrally managed, real-time bed-tracking portal covering all public hospitals and eventually private facilities" — confirming this gap is unresolved.

---

## What's Actually Usable for a Hackathon

| Source | What you get | Freshness | API? |
|--------|-------------|-----------|------|
| ABDM HFR | Facility list + IDs | Live (registration) | Yes (identity only) |
| NHRR / NHP | Aggregate bed counts by state | Annual | No |
| data.gov.in | State-level bed totals | 2–4 years old | No |
| Kaggle datasets | Hospital list + bed counts | 2018 | No |
| COVID dashboards | Historical occupancy (some states) | Dead | No |

**Practical path:** Use ABDM HFR as facility registry baseline + NHP data for bed-count priors. Synthetic or simulated occupancy data will likely be needed for any ML demo. Partnership with a single hospital for real data is more realistic than scraping government portals.

> **★ INSIGHT (build plan)** — Phase 1 ingest = HFR identity layer + NHP state-level bed totals + Kaggle 2018 hospital list, all cleaned into one Delta table. Synthetic occupancy on top, calibrated per state ratios. The data being old/incomplete is *the problem we're solving*, not a blocker for the build.

---

## Sources
- https://abdm.gov.in/strapicms/uploads/HFR_SOP_for_verifiers (ABDM HFR SOP)
- https://byjus.com/free-ias-prep/national-health-resource-repository-project/ (NHRR overview)
- https://journals.sagepub.com/doi/10.1177/09720634221077322 (Mapping Healthcare Data Sources in India)
- https://www.data.gov.in/keywords/Hospitals (OGD Platform)
- https://www.kaggle.com/datasets/fringewidth/hospitals-in-india
- https://www.kaggle.com/datasets/dheerajmpai/hospitals-and-beds-in-india
- https://www.preprints.org/manuscript/202509.2106 (real-time portal proposal, 2025)
- https://www.mercatus.org/system/files/rajagopalan-india-healthcare-mercatus-v2.pdf
