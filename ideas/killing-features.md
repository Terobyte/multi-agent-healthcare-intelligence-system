# Killing Features — Working List

Living doc. Trim ruthlessly.

A "killing feature" = one capability that makes a family in Bihar / a doctor in a district hospital / an ASHA worker say *"I needed exactly this, today."* If we can't say that out loud, it's a feature, not killing.

Ranking dims (apply per candidate):
- **Pain killed** (1–5)
- **Demo-able in 24h** (1–5)
- **Hard to copy** (1–5)
- **Sponsor-fit (Databricks / data scale)** (1–5)

---

## Synthesis: Two Killing Features Stacked

The team's brainstorm produced 4 agents (Cleaning, Prediction, Routing, Alert) plus a voice-call idea. After analysis, only **two of these are pitch-level killing features**. The rest are infrastructure that supports them.

### KILLING FEATURE A — Voice-Verified Prediction

We don't claim live data. We claim **calibrated prediction with confidence bands, spot-checked by voice when it matters most**.

```
                       ┌─────────────────────────┐
[Dirty 10k records] ──▶│ Ingest + Clean          │ ◀── infrastructure
                       │ (Lakehouse + vector)    │
                       └────────────┬────────────┘
                                    ▼
                       ┌─────────────────────────┐
       voice samples ─▶│ Predictor               │
        feed back as   │ history + recent signals│
        ground truth   │ → P(bed | hospital, t)  │
                       └────────────┬────────────┘
                                    ▼
            ┌────────────────────────────────────────┐
            │ Verifier (Voice Agent)                 │
            │ triggered ONLY when:                   │
            │   • patient is about to travel there   │
            │   • prediction confidence < 0.7        │
            │   • last sample > 2h old               │
            │ 15-sec call in vernacular, 1 question  │
            └────────────────────┬───────────────────┘
                                 ▼
            ┌────────────────────────────────────────┐
            │ Router                                 │
            │ ranks 3 hospitals by                   │
            │ P(bed) × travel × cost × quality       │
            └────────────────────┬───────────────────┘
                                 ▼
            ┌────────────────────────────────────────┐
            │ Patient / ASHA UI (vernacular)         │
            └────────────────────────────────────────┘
```

**Pitch narrative:**
> *"Other systems either lie (stale dashboards) or burden hospitals (constant calling). We do neither. We predict from history, and only verify by voice when a patient is actually on the road and the prediction is uncertain. That's 10× fewer calls to hospital staff than naive verification, and 10× more accurate than static dashboards."*

**Why this is one feature, not two:** The voice agent without prediction = naive front-desk spam (which is what the team explicitly rejected). The prediction without voice = ghost-bed dashboard rebrand. They only kill *together*.

### KILLING FEATURE B — Inter-Facility Transfer Copilot

The team's favorite scenario (point #3): doctor at small hospital says *"move them to a tertiary center."* Today the family scrambles. Our agent does it in one screen:
- ranks 3 receiving hospitals by capability + Predictor's bed estimate + travel time
- packages records (HL7 / FHIR / OCR'd paper chart)
- books an ambulance via 108 or private partner
- opens a structured handoff between sending and receiving doctors

**Why killing:** This is the moment families lose people they shouldn't have lost. Almost no software touches it end-to-end. We can pitch B2D2 (doctor-to-doctor) and patient-side simultaneously.

**Open Q:** Can we get a read on 108 dispatch APIs? Convincingly fake ambulance booking in a demo?

---

## Infrastructure (table stakes, not pitch headline)

These exist in our build but **don't lead the pitch**. From the teammate's 4-agent design, three become infrastructure:

- **Data Cleaning Agent** — ingests 10k messy records, normalizes addresses/specialties, dedupes. Lakehouse layer. Critical for Databricks judges; not a wow moment by itself.
- **Routing layer** — consumer of Predictor. Pure ranking logic, no ML.
- **Alert / Notification system** — SMS / WhatsApp / push channel for "transfer accepted", "bed reserved 30 min". Delivery plumbing.

---

## Auxiliary Capabilities (compose into A or B)

These were standalone candidates earlier but really fold into A or B as UX surfaces or extra signals.

### Vernacular Triage Front-end → folds into A's UI
"Mere bachche ko bukhar hai" via WhatsApp → Predictor + Router. Triage logic is a thin LLM layer in front of the UI.

### Cost-Truth Advisor → folds into A's recommendation card
Each hospital recommendation shows medical + non-medical cost (travel, lost wages, caregiver food). The 55M-into-poverty stat is mostly non-medical.

### ASHA Co-Pilot → folds into A as a distribution channel
A's UI variant for frontline workers: triage + referral generator + journey tracker. Same backend, different front-end role.

### SMS / IVR Fallback → folds into A as a delivery channel
For users with no smartphone / no data. Same Predictor + Router output, delivered as SMS / IVR.

### Bridge Doctor Mode → folds into B as a sub-flow
Two doctors on a transfer call get a structured shared screen with patient summary, vitals, OCR'd chart, one-tap accept / reject.

---

## Discussion Prompts

- **Demo path:** A only? A + B? B only? (A is denser; B is more emotional)
- **Pitch headline:** lead with A ("Voice-Verified Prediction") or B ("Transfer Copilot")?
- **What's missing?** especially anything Databricks-specific — geospatial scale, Lakehouse Monitoring, MLflow registry for the Predictor, vector search over hospital descriptions
- **Fake vs real voice agent for demo?** real voice call to a stub PBX number is more impressive than a recording — but riskier on demo day

---

## Killed / Deprioritized

(move things here as we cut them — keep rationale visible)

- *(none yet)*
