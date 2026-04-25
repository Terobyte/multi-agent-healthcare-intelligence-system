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

## Build Order (Phased Strategy)

**Strategy:** ship everything, but in phases. Each phase ends in a state that is *itself* demo-ready. If we run out of time, we cut from Phase 3, never from Phase 1 or 2. Crazy ideas land in Phase 3 by design — they're high-risk, high-wow, and we save them for after the foundation is solid.

### Phase 1 — Foundation (the spine has to work before anything fancy)

These are table stakes; without them, the demo can't start.

- [ ] Ingest + clean 10k messy hospital records → Lakehouse / Delta table
- [ ] Geospatial index (lat/lon, district, state) ready for distance queries
- [ ] Predictor v1: **history-only baseline** for P(bed | hospital, time). No voice yet.
- [ ] Router: rank 3 hospitals by P(bed) × travel × specialty match
- [ ] Patient web UI: input symptom or city → see 3 ranked hospitals on a map
- [ ] One vernacular: Hindi text in/out (call the rest "Phase 3")

**Phase 1 demo-ready state:** *"Type 'fever, Lucknow' → see 3 hospitals with confidence-banded bed predictions on a map."*

### Phase 2 — The Two Killers Light Up (A and B core working)

This is the minimum demo we'd be proud of in front of judges.

- [ ] **Voice Verifier (KILLER A):** stub-call agent that reads a script in Hindi, parses a Yes/No/Number response. Mock-call mode for the demo (recorded handset audio replayed).
- [ ] Confidence-triggered verification logic (call only when prediction < 0.7 OR sample > 2h old)
- [ ] Verifier results feed back as ground truth into Predictor
- [ ] **Transfer Copilot (KILLER B) core:** doctor-side flow — pick a sending hospital, get 3 receiving recommendations, generate referral packet (PDF + structured FHIR snippet)
- [ ] Cost-Truth card on every recommendation (medical + non-medical estimate)
- [ ] WhatsApp-style chat front-end for vernacular triage (folds into A's UI)

**Phase 2 demo-ready state:** *"Mother types symptom in Hindi → Router shows 3 hospitals with cost truth → judge clicks 'verify availability' → mock voice call plays → confidence updates live. Then: switch to doctor view, click 'refer this patient' → 3 receiving hospitals + referral packet generated."*

### Phase 3 — Crazy Wow (only after Phase 2 works)

These are the moonshots. Each one alone is a "holy shit" moment in a demo. None is required for a credible pitch.

- [ ] **LIVE voice call** during the demo — real outbound dial to a stub PBX number, real STT/TTS, real LLM in the middle. (Highest wow. Highest risk.)
- [ ] **Ambulance auto-dispatch** — fake 108 booking with countdown ("ambulance ETA 14 min")
- [ ] **Bridge Doctor Mode** — live shared screen between sending and receiving doctors, OCR'd handwritten chart, one-tap accept/reject
- [ ] **SMS / IVR fallback** — actual SMS sent to a Twilio India number during demo, response visible on screen
- [ ] **ASHA Co-Pilot tablet view** — separate UI showing the same backend used by frontline workers
- [ ] **Crowdsourced ground-truth signals** — patient we routed yesterday auto-prompts "did you find a bed?" → feeds back into Predictor
- [ ] **MLflow + Lakehouse Monitoring** showcase — Predictor model in registry, drift dashboard live (Databricks-specific judges' bait)
- [ ] More vernaculars: Bhojpuri, Marathi, Tamil, Bengali (one extra is enough for the demo)

**Phase 3 picking rule:** at the start of Phase 3, **pick at most 3** crazy items based on (a) what's already half-working, (b) what's lowest-risk-on-demo-day, (c) which gives the biggest "did they really build that?" reaction. The rest go on the roadmap slide.

---

## Discussion Prompts

- **Phase 1 ETA?** When can we declare the spine working? Need this date to know how much Phase 3 is actually realistic.
- **Who owns each phase?** A two-killer build needs at least one person on Predictor/Router and one on Voice/UI by Phase 2. Transfer Copilot is a third track in Phase 2.
- **Phase 3 wishlist top-3?** Each of us should pick the 3 we'd most love to see live. Compare lists, find overlap, that's the priority.
- **Databricks-specific signals to bake in early:** vector search over hospital descriptions in Phase 1, MLflow model registry for Predictor in Phase 2, Lakehouse Monitoring on the Predictor's drift in Phase 3. These cost ~nothing extra if we plan for them now and a lot if we retrofit.

---

## Killed / Deprioritized

(move things here as we cut them — keep rationale visible)

- *(none yet)*
