# Challenge 3 — Agentic Healthcare Maps (Databricks)

> Source: hackathon brief shared by the team.

## The Mission

Beyond Maps — Building the Nervous System for Indian Healthcare.

The challenge asks the team to turn 10,000 messy hospital records into a live intelligence network. The deeper ask: India's healthcare system suffers from extreme information asymmetry. Families in Bihar, rural Maharashtra, or tribal Odisha do not need a "Google Maps with more pins." They need an operational brain that understands intent, predicts availability, negotiates distance vs. quality trade-offs, and communicates in their language and bandwidth reality.

Goal: build an Agentic Healthcare Intelligence Network — not a static directory, but a multi-agent system running on Databricks that ingests dirty, fragmented data, verifies it in real time, reasons over it, and serves actionable guidance to patients and field workers.

## Human Context

- **55 million Indians** pushed into poverty annually due to catastrophic health expenditure (WHO India, 2023). A significant portion is non-medical: travel, food, lost wages for caregivers on futile multi-hospital journeys.
- **Inverse Care Law**: those who need care most have the least information about it. Rural India = 70% of population, 30% of hospital beds.
- **Ghost Bed phenomenon**: COVID-era state bed dashboards are now static, unmaintained, or disconnected from actual HMIS. UP district-hospital field study (2024): online bed data was correct only 34% of the time.
- **Language fracture**: 90% of health-tech in India is built in English. Only ~10% of Indians speak English fluently.

## Team Read on the Brief

From the team Zoom (verbatim points worth keeping):

1. The problem statement makes sense — patients often have to physically go to the hospital just to find out if there's space.
2. Most hospitals run offline / local systems for patient data.
3. When a patient deteriorates, doctors tell families to move them to a specialized hospital — transferring records, finding a receiving hospital, and renting an ambulance falls on the family. **(We like this scenario — it's underserved.)**
4. The "constantly call the front desk" approach is unrealistic — front desks are overwhelmed and won't pick up calls every 2 minutes.

## Implication for Design

- **Real-time availability cannot rely on burdening hospital staff.** Must be either predicted, crowdsourced, pulled from official feeds, or verified via voice-AI (low staff load).
- **Inter-facility transfer coordination** is a real, unsolved software gap.
- **Patient-facing UX** has to be vernacular and low-bandwidth.
