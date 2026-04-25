# Aarogya AI — Trust Verification & Desert Mapping Spec

> **Approach:** Two-agent extractor/validator over messy 10k records, producing a Trust Score with prediction intervals and a PIN-coded Medical Desert Map for NGO planners
> **Source:** Teammate brainstorm (`aarogya_brainstorm_full.html`, 2026-04-25) — friend 1's proposed path
> **Deployment target:** Databricks-native (Delta Lake medallion + Mosaic AI Vector Search + Unity Catalog + Genie Code agent + MLflow 3 tracing)
> **Challenge:** Serving A Nation — Building Agentic Healthcare Maps for 1.4 Billion Lives (Challenge 03, see `docs/challenge-brief.md`)
> **Last updated:** 2026-04-25

---

## 1. Executive Summary

A multi-agent system whose **only job** is to turn the 10,000 messy Indian facility records into trustworthy, queryable, geographically-honest intelligence. The killer feature is **two-agent contradiction detection**: one agent extracts capability claims, a second independent agent doubts them — together they catch the lies a single-pass system cannot.

**Three architectural choices that define this approach:**

1. **Trust comes from two agents disagreeing, not one agent extracting.** Extractor reads the claim ("ICU 24/7"), Validator reads the rosters and equipment logs ("but no night-shift staff, no ventilators"). Disagreement *is* the signal — every contradiction lowers the field's confidence.
2. **Trust scores ship with prediction intervals.** Every facility gets `score ± CI`, every field gets `evidence_completeness`. The brief's Areas of Research explicitly asks for this; we surface it on every card.
3. **The map is the product.** A PIN-code medical desert overlay reveals where dialysis, oncology, and trauma capability is *missing*. NGO and government planners are the second user class; the same trust pipeline serves both.

**What this approach deliberately does not include** (and why that is OK for a 24h hack):
- No transfer coordination, no atomic booking, no operational handoff. The bet is that *fixing the data* is itself a complete product.
- No real-time stream, no IntakeAgent handshakes, no outcome loop. Trust is computed once, displayed always — refreshed by re-running the pipeline.
- No voice fallback. The 10k records are the source of truth; voice would be a layer on a different system.

**Why this matches the brief:**

| Brief weight | Component covering it |
|---|---|
| **35% Discovery & Verification** | Two-agent Extractor + Validator — independent doubt is the verification mechanism |
| **30% IDP Innovation** | Free-form facility notes → Pydantic-typed structured facts with source-sentence citations |
| **25% Social Impact** | Medical Desert Dashboard — PIN-coded gap map for NGOs and Govt planners |
| **10% UX/Transparency** | MLflow 3 tracing + per-field confidence shown on every card |

**Why Databricks-native:** Delta Lake medallion (Bronze→Silver→Gold) is the central artifact. Mosaic AI Vector Search powers semantic retrieval ("emergency surgery Bihar" hits the right rows even without keyword overlap). Unity Catalog tags sensitive fields and gates access tiers (NGO / public / admin). Every recommendation traces to the exact sentence — judges click and see the evidence.

---

## 2. Architecture Diagram

```
                  ┌─────────────────────────────────────────┐
                  │  Databricks App (React)                  │
                  │  ├── Patient search (symptom → facility) │
                  │  └── NGO Desert Dashboard (PIN map)      │
                  └────────────────────┬────────────────────┘
                                       │ HTTPS
                                       ▼
                  ┌─────────────────────────────────────────┐
                  │  Query Orchestrator (Genie Code)         │
                  │  Single agent, multi-step reasoning over │
                  │  Gold table. MLflow 3 traces every step. │
                  └────────────────────┬────────────────────┘
                                       │
                                       ▼
              ┌───────────────────────────────────────────┐
              │  GOLD TABLE — trust-scored, citation-     │
              │  indexed, Pydantic-validated              │
              └────────────────────┬──────────────────────┘
                                   │
                ┌──────────────────┴──────────────────┐
                ▼                                     ▼
        ┌───────────────┐                   ┌────────────────┐
        │ Extractor     │  ←── disagree? ──▶│ Validator      │
        │ Agent         │                   │ Agent          │
        │               │                   │                │
        │ Reads: notes, │                   │ Reads: rosters,│
        │ free text     │                   │ equipment logs │
        │               │                   │                │
        │ Emits claims  │                   │ Doubts claims  │
        │ + source cite │                   │ + flags contra │
        └───────┬───────┘                   └────────┬───────┘
                │                                    │
                └──────────────┬─────────────────────┘
                               ▼
              ┌──────────────────────────────────────┐
              │  Trust Scorer (UC function)          │
              │  combines extraction confidence ×    │
              │  contradiction count × evidence      │
              │  completeness → score 0-100 + CI      │
              └────────────────┬─────────────────────┘
                               ▼
              ┌──────────────────────────────────────┐
              │  Medical Desert Aggregator            │
              │  group by PIN × specialty × trust ≥ τ │
              │  → coverage gap heatmap               │
              └──────────────────────────────────────┘

   ─────────── DATA PLANE ───────────
                  ┌─────────────────────────────────────────┐
                  │  Lakehouse (Delta + Unity Catalog)       │
                  │  bronze (raw 10k + VF schema)            │
                  │   → silver (geocoded, deduped, normed)   │
                  │   → gold  (trust-scored, citation-ready) │
                  │  + Mosaic AI Vector Search (semantic)    │
                  │  + MLflow 3 Registry + Tracing           │
                  │  + Unity Catalog (NGO/public/admin tags) │
                  │  + Virtue Foundation pydantic schema     │
                  └─────────────────────────────────────────┘
```

---

## 3. Components

### 3.1 Query Orchestrator (Genie Code)

- **Stack:** Genie Code agent over Gold Delta table
- **Owner:** Tero (configuration + agent prompt)
- **Folder:** `tero/orchestrator/`
- **What it does:** single agent, multi-step. Receives free-text query (Hindi or English), expands to specialty + filter constraints, retrieves trust-scored candidates, returns ranked list with citations.
- **Why one agent, not a supervisor:** the brainstorm explicitly keeps orchestration simple. The intelligence lives in the *data* (Trust Score), not in agent-to-agent choreography.
- **MLflow 3 tracing** on every step — each retrieved row links back to its citation index.

### 3.2 Extractor Agent (IDP)

- **Stack:** LLM (gpt-4o or Claude) + Vector Search retrieval over facility notes, registered as UC function
- **Owner:** Mubarak (NVIDIA RAG cert + IDP background)
- **Folder:** `mubarak/extractor/`
- **What it does:** for each facility row, reads all free-form fields (equipment notes, staff remarks, capability lists in mixed Hindi/English) and emits a Pydantic object of structured claims, each with a **source sentence index** for traceability.
- **Output:**
  ```json
  {
    "hospital_id": "h_3421",
    "claims": {
      "icu_beds":          {"value": 12, "source": "facility_note_p2_s1"},
      "specialties":       {"value": ["cardiology","neurology"], "source": "capability_list"},
      "24_7_emergency":    {"value": true, "source": "facility_note_p1_s3"},
      "anesthesiologist":  {"value": null, "source": null},
      "ventilators":       {"value": 4, "source": "equipment_log_row_22"}
    },
    "extraction_confidence": 0.81,
    "trace_id": "tr_ext_abc"
  }
  ```

### 3.3 Validator Agent (independent doubter)

- **Stack:** Second LLM (deliberately different model from Extractor — we want independence) + access to staff rosters, equipment logs, pharmacy lists
- **Owner:** Mubarak (lead) + Danish (rule rules + Hindi/Urdu cross-check)
- **Folder:** `mubarak/validator/`
- **What it does:** for each Extractor claim, looks for *evidence against it*. Emits contradiction flags with confidence and evidence pointers.
- **Independence is the point:** running both passes with the same model would correlate errors. Different models, different prompts, different retrieval slices.
- **Rule examples:**
  - Claim "Advanced Surgery 24/7" + roster shows no anesthesiologist → flag, contradiction confidence 0.92
  - Claim "ICU 12 beds" + equipment log shows 4 ventilators → flag, partial inconsistency 0.6
  - Claim "Dialysis available" + no nephrologist on roster → flag 0.85
- **Output:**
  ```json
  {
    "hospital_id": "h_3421",
    "flags": [
      {
        "field": "24_7_emergency",
        "rule": "no_night_staff",
        "evidence": "staff_roster_row_44 shows 9-5 only",
        "contradiction_confidence": 0.88
      }
    ],
    "validated_fields": ["icu_beds", "ventilators"],
    "trace_id": "tr_val_xyz"
  }
  ```

### 3.4 Trust Scorer

- **Stack:** Unity Catalog Python function combining Extractor + Validator outputs
- **Owner:** Mubarak (lead) + Tero (UC function plumbing)
- **Folder:** `mubarak/trust-scorer/`
- **Inputs:**
  - Extractor's per-field `extraction_confidence`
  - Validator's per-field `contradiction_confidence` (negative signal)
  - `evidence_completeness` (how many fields had a citation source)
- **Score formula (v1):**
  ```
  trust_field = extraction_confidence × (1 - contradiction_confidence) × evidence_completeness
  trust_facility = weighted_mean(trust_field, weights=field_importance)
  CI_facility = std_error_propagation(field_CIs)
  ```
- **Output written to Gold:**
  ```json
  {
    "hospital_id": "h_3421",
    "trust": 0.74,
    "trust_ci": 0.09,
    "field_scores": {
      "icu":          {"value": 0.91, "ci": 0.04},
      "emergency_24_7":{"value": 0.32, "ci": 0.12, "flag": "no_night_staff"},
      "dialysis":     {"value": 0.0,  "ci": 0.0,  "flag": "no_nephrologist"}
    },
    "evidence_completeness": 0.78,
    "trace_id": "tr_score_123"
  }
  ```

### 3.5 Medical Desert Aggregator

- **Stack:** SQL view over Gold table + Lakeflow / DLT job, refreshed on pipeline run
- **Owner:** Arushi (dashboard) + Danish (aggregation pipeline)
- **Folder:** `arushi/desert-map/`
- **What it does:** group facilities by PIN code × specialty. For each PIN, count facilities where `field_score ≥ 0.6`. PINs with `count = 0` for a specialty become **deserts** for that specialty.
- **Heatmap layers:**
  - Dialysis deserts (red where count=0)
  - Oncology gaps (amber where count<2)
  - Trauma voids (red where count=0 within 50km radius)
- **Brief weight:** the entire 25% Social Impact rubric pillar.

### 3.6 Vector Index

- **Stack:** Mosaic AI Vector Search (storage-optimized)
- **Owner:** Danish
- **Folder:** `mian/vector-index/`
- **Indexes:**
  - Each facility note as one chunk (sentence-level for citation)
  - Symptom → specialty corpus (Hindi/English)
- **Used by:** Extractor (for field-by-field retrieval), Query Orchestrator (for semantic facility search).

### 3.7 Data Plane

- **Lakeflow / DLT** medallion pipeline:
  - **Bronze:** raw 10k XLSX + Virtue Foundation schema column mapping. Rows with missing critical fields flagged but kept (do not silently drop).
  - **Silver:** addresses geocoded (fuzzy → PIN lookup), duplicates resolved, specialty taxonomy normalized, mixed-language fields detected and tagged with source language.
  - **Gold:** Trust-scored output of Extractor → Validator → Trust Scorer.
- **Unity Catalog:** every field tagged with sensitivity (`public` / `ngo_only` / `admin`). Lineage auto-tracked through DLT.
- **MLflow 3 Registry:** Extractor and Validator prompts versioned; every inference traced.

### 3.8 Databricks App (UI)

- **Stack:** React + appkit SDK + Leaflet/Mapbox
- **Owner:** Arushi
- **Folder:** `arushi/app/`
- **Two surfaces:**
  - **Patient search:** symptom box (Hindi/English) → ranked facility cards with trust score + CI + flagged contradictions visible
  - **NGO Desert Dashboard:** map of India by PIN, toggleable specialty layers (dialysis / oncology / trauma), filter by minimum trust threshold

---

## 4. Data Flow — The Killer (Extract → Doubt → Score)

```
[Pipeline run, scheduled or manual]
    │
    ▼
[Bronze]  10k raw rows, mixed Hindi/English, free-form notes
    │
    ▼
[Silver]  geocoded + normalized + deduped
    │
    ▼
[Extractor Agent]  per row, per field
    │     ├─ reads facility_note_p2_s1 → "ICU 12 beds, 24/7 emergency, advanced surgery"
    │     └─ emits structured claims with source sentence indices
    │
    ▼
[Validator Agent]  same row, independent retrieval
    │     ├─ reads staff_roster_row_44 → "Dr. Sharma 9-5 only, no night shift"
    │     ├─ reads equipment_log_row_22 → "4 ventilators"
    │     ├─ flags "24_7_emergency": no night staff (contradiction 0.88)
    │     └─ flags "advanced_surgery": no anesthesiologist (contradiction 0.92)
    │
    ▼
[Trust Scorer]
    │     ├─ icu (12 beds backed by ventilator count): 0.91
    │     ├─ 24_7_emergency: 0.32 (extraction was confident, contradiction strong)
    │     ├─ advanced_surgery: 0.18 (anesthesiologist missing kills it)
    │     └─ overall trust: 0.61 ± 0.11
    │
    ▼
[Gold table]  written. Pipeline complete.

   ──── At query time ────
[User] types "इमरजेंसी सर्जरी, बिहार"
    │
    ▼
[Query Orchestrator (Genie Code)]
    │     ├─ Vector Search retrieves candidates by semantic match
    │     ├─ filter by trust_field ≥ 0.6 for "advanced_surgery"
    │     └─ rank by trust × proximity
    │
    ▼
[Patient sees]  3 facility cards, each with:
    • Trust score with CI
    • Per-field breakdown — "advanced_surgery 0.84, dialysis 0.0 (no nephrologist)"
    • Click any field → MLflow trace → exact source sentence
```

---

## 5. Data Flow — NGO Desert Dashboard

```
[NGO planner opens Desert Dashboard]
    │
    ▼
[Aggregator] reads Gold, groups by PIN × specialty
    │     ├─ PIN 800001 (Patna East): cardiology=12, dialysis=0, oncology=1
    │     ├─ PIN 802101 (Bihar rural): cardiology=2, dialysis=0, oncology=0
    │     └─ PIN 845401 (Madhubani): cardiology=0, dialysis=0, oncology=0
    │
    ▼
[Map renders] India PINs colored by gap severity
    │     ├─ filter: "show me dialysis deserts"
    │     ├─ filter: "show me PINs where oncology gap > 50km"
    │     └─ filter: "trust threshold ≥ 0.7" (only count high-confidence facilities)
    │
    ▼
[NGO planner] clicks Madhubani → sees:
    "0 dialysis facilities within 80km radius. Nearest verified facility: 142km
     (Hospital X, trust 0.72). Population served: 4.2M. Recommended action:
     mobile dialysis unit deployment."
```

---

## 6. Integration Contracts

Each agent emits a fixed JSON shape. Pydantic-validated. **VF Schema is the base** (`from contracts.schemas import ...`).

```
ExtractorAgent.output    → { hospital_id, claims{field: {value, source}}, extraction_confidence, trace_id }
ValidatorAgent.output    → { hospital_id, flags[{field, rule, evidence, contradiction_confidence}], validated_fields[], trace_id }
TrustScorer.output       → { hospital_id, trust, trust_ci, field_scores{field: {value, ci, flag?}}, evidence_completeness, trace_id }
DesertAggregator.output  → { pin: {specialty: {count, min_trust, nearest_km}} }
QueryOrchestrator.output → { query, ranked_facilities[{hospital_id, trust, field_breakdown, citations[]}], trace_id }
```

**Why this contract surface is small on purpose:** there are no operational handoffs (no booking, no transfer, no voice). The only contract that matters is "what does the data layer hand to the UI." That keeps integration day short.

**Integration day** (last 4 hours):
1. Each owner runs `pytest contracts/test_my_output.py` — output matches Pydantic schema
2. Query Orchestrator swaps mock Gold reads → real Gold table
3. Dashboard swaps mock `desertAggregator.json` → real aggregator output
4. End-to-end test against demo dataset

---

## 7. Team Mapping

| Person | Owns | Project Folder | Stack | Risk |
|---|---|---|---|---|
| **Tero** | Query Orchestrator (Genie Code) + UC plumbing for Trust Scorer + integration + demo theatre + pitch | `tero/orchestrator/` | Python, Genie Code, MLflow 3 | Medium — orchestration is one agent, not a swarm |
| **Mubarak** | Extractor Agent + Validator Agent + Trust Scorer logic | `mubarak/extractor/`, `mubarak/validator/`, `mubarak/trust-scorer/` | Python, LLM (gpt-4o + Claude for independence), Vector Search, Pydantic | High — two agents + scoring; the killer |
| **Danish** | DLT pipeline (Bronze→Silver→Gold) + Vector Index + Validator rule rules + Hindi/Urdu cross-check | `mian/dlt-pipeline/`, `mian/vector-index/`, `mian/validator-rules/` | Python, Lakeflow/DLT, geocoding, sklearn | High — pipeline is critical path; **stub gold table H 1** to unblock |
| **Arushi** | Databricks App (React) — patient search + **NGO Desert Dashboard** + submission | `arushi/app/`, `arushi/desert-map/` | React + appkit SDK + Leaflet/Mapbox | Medium — dashboard is the social-impact face of the demo |

**Notes:**
- The team is the same 4 people as the existing multi-agent design spec, mapped to a different (smaller) component surface.
- Mubarak owns the verification core (Extractor + Validator + Trust Scorer). This is consistent with his profile (NVIDIA RAG + IDP).
- No Voice MCP, no IntakeAgent, no Outcome Loop, no Atomic Booking owners — those are not in scope here.

---

## 8. Build Order — 18-Hour Schedule

The brainstorm specifies three phases: Data foundation → Agent intelligence → Output and traceability. We map them to hours.

### H 0-1 — Provisioning + spikes (everyone)
- [ ] [Tero] Databricks workspace + UC perms for all 4 owners
- [ ] [Tero] **Validate Free Edition supports**: Genie Code, Vector Search, MLflow 3 Tracing. Fall back if anything paid-only.
- [ ] [Tero] Download `VF_Hackathon_Dataset_India_Large.xlsx`, extract Virtue Foundation pydantic schema → `contracts/schemas.py`
- [ ] [Danish] **STUB gold table:** 50 hardcoded trust-scored hospitals committed to Delta within first hour. Unblocks Query Orchestrator, Dashboard, NGO map.
- [ ] [Mubarak] hello-world Extractor spike: one row, one field, one citation
- [ ] [Arushi] appkit SDK hello-world Databricks App spike

### H 1-7 — Phase 1: Data foundation
- [ ] [Danish] DLT pipeline real: Bronze → Silver, geocoding, dedupe, language detection
- [ ] [Danish] Vector Search index built over silver facility-note sentences
- [ ] [Danish] Unity Catalog field tagging (public / ngo_only / admin)
- [ ] [Tero] Query Orchestrator skeleton reading stubbed Gold
- [ ] [Arushi] patient-search page rendering stubbed facility cards from mock

**H 7 phase 1 demo state:** *"Type 'fever, Lucknow' → 3 stub hospitals on map with mock trust scores."*

### H 7-13 — Phase 2: Agent intelligence
- [ ] [Mubarak] Extractor v1: per-row, per-field claim extraction with source sentence indices, registered as UC function
- [ ] [Mubarak] Validator v1: independent doubter, flags with evidence pointers
- [ ] [Mubarak] Trust Scorer combining both, writing to Gold
- [ ] [Danish] Validator rule pack (no_night_staff, no_anesthesiologist, no_nephrologist, ICU-without-ventilators, etc.)
- [ ] [Tero] Query Orchestrator: real Gold reads, MLflow 3 traces wired
- [ ] [Arushi] facility-card UI: trust score + CI + per-field breakdown + click-to-trace

**H 13 phase 2 demo state:** Real 10k → real trust scores → real cards with click-to-source.

### H 13-16 — Phase 3: Output + traceability + desert
- [ ] [Danish/Arushi] Medical Desert Aggregator + heatmap layer
- [ ] [Arushi] NGO Desert Dashboard with PIN-by-PIN gap filtering
- [ ] [Mubarak] MLflow 3 row-level citation panel: click any field → see exact sentence
- [ ] [Tero] Genie Code multi-step query polish ("rural Bihar appendectomy with part-time doctors" demo query)

### H 16-17 — Integration + contract tests (everyone)
- [ ] Each owner runs `pytest contracts/test_my_output.py`
- [ ] [Tero] swap stubs in Query Orchestrator → real outputs
- [ ] End-to-end: patient search + desert dashboard

### H 17-18 — Demo rehearsal + slides
- [ ] 3 full demo runs against real backend
- [ ] [Arushi] submission package: README, demo video, Devpost writeup, GitHub polish

---

## 9. Demo Theatre Discipline

**Rule:** the brainstorm explicitly identifies "trust scores with intervals" and "click-to-source" as the differentiators. Every demo second must showcase one of:

- [ ] Patient search returns ranked cards — trust + CI + flagged contradictions visible
- [ ] Click any field on a card → MLflow trace panel opens → exact source sentence highlighted in facility note
- [ ] Validator-flagged hospital shows visibly demoted ("Advanced Surgery without Anesthesiologist" — score 0.18, red badge)
- [ ] Genie Code chat: judge types multi-attribute query → multi-step output renders with citations
- [ ] NGO Desert Dashboard toggled on: dialysis layer red-highlights Bihar PINs
- [ ] Vector Search top-k visible somewhere (citation source)

**Click-to-source is the single most important demo move.** This is the rubric-aligned wow: 30% IDP + 10% transparency, both visible in one click.

---

## 10. Demo Script (90 seconds)

**00:00-00:15** — Opener slide: "10,000 facility records. Free-form, mixed Hindi-English, contradictory. Today they become an intelligence layer."

**00:15-00:35** — Patient search opens. Type «बुखार और सीने में दर्द, पटना» (fever, chest pain, Patna). Genie Code multi-step traces in dev panel. 3 hospitals render with 4-factor trust + CI.

**00:35-00:50** — Click a flagged field on Hospital C: *"Advanced Surgery: 0.18, contradiction — no anesthesiologist on roster."* MLflow trace panel slides in. Source sentence highlighted in original note: *"Advanced Surgery available 24/7."* Roster row 44 highlighted: *"Dr. Sharma 9-5 only."*

**00:50-01:05** — Open Genie Code chat. Judge prompt: "Rural Bihar appendectomy with part-time doctors." Multi-step renders: extract → score → return with citations. Table populates.

**01:05-01:25** — Switch to NGO Desert Dashboard. Toggle dialysis layer. Bihar lights up red. Click PIN 845401: "0 dialysis within 80km, population 4.2M, nearest verified 142km." Toggle oncology: different gaps emerge.

**01:25-01:30** — One-line close: *"We turned 10,000 messy records into a trust map. Every score has an interval. Every card has a citation. That's how India finds care it can rely on."*

---

## 11. Fallback Strategy

| Failure | Swap to | Setup before demo |
|---|---|---|
| Genie Code query times out | Pre-recorded screen capture + slide overlay "captured live" | Record H 16-17 |
| Databricks App deploy down | Backup deploy on Vercel — URL change but flow identical | Keep Vercel deploy alive H 16-17 |
| Validator misfires (false contradiction at demo) | Hand-curate 3 demo hospitals known to behave | Curate H 14-15 |
| Extractor slow on full 10k | Pre-compute Gold offline; demo reads frozen Gold | Pre-compute H 13 |
| MLflow trace panel slow | Static screenshot in slide instead of live click | Screenshot H 16-17 |
| Desert Dashboard slow on full geo data | Pre-aggregate into static GeoJSON, render from disk | Pre-aggregate H 15 |

**Rule:** every "live" demo moment must have a pre-recorded version that's been tested.

---

## 12. Risks & Open Questions

| Risk | Severity | Mitigation |
|---|---|---|
| Brief explicitly names Genie Code (not Spaces) — Free Edition support unverified | High | Tero H 0-1 spike validation; fall back to Genie Spaces if blocked |
| Validator independence is hard if both agents share retrieval context | High | Use deliberately different model (Claude for Validator if Extractor is gpt-4o) and disjoint retrieval slices (notes vs rosters) |
| Two-agent architecture is less visually impressive than a swarm of 5 — judges may not see the depth | High | Click-to-source MLflow trace is the visualization surface; rehearse the click moment |
| Trust score formula is hand-rolled, not learned | Medium | Acknowledge in pitch; v2 would learn from feedback. Brief Areas of Research mentions intervals — we have them. |
| 10k records source format unknown (VF schema) — Danish's DLT depends on it | High | Danish H 0-1 sniff sample; **stub gold table H 1 unblocks team regardless** |
| No operational layer (no booking, no transfer) — judges may ask "what do families do with this?" | Medium | Pitch frames Aarogya AI as the *intelligence layer*; partners (108, ABDM) consume the API. Be honest. |
| Extractor + Validator combined latency on 10k rows | Medium | Pre-compute offline; pipeline runs in batch, not at query time |
| Hindi/English language detection in Silver tier | Medium | Danish (Urdu native) cross-checks; fall back to language-tagged passthrough if detection fails |
| Mubarak owns 3 components (Extractor, Validator, Scorer) | Medium | Trust Scorer is just a Python function over both outputs — Tero pairs on UC plumbing |
| All 4 need Databricks workspace + UC perms | High | Tero provisions H 0; verify before everyone starts |

---

## 13. Out of Scope

- Transfer coordination, atomic booking, ambulance dispatch (separate operational system)
- Real-time bed availability streaming or hospital handshakes
- Voice interface (web text input only)
- Outcome learning loop or post-routing feedback
- Multi-language beyond Hindi/English in the demo
- Real ABDM API integration
- Mobile-native app (Databricks App is web-only)
- WhatsApp integration

---

## 14. Success Criteria

**Demo-day pass:**
- Patient types Hindi/English symptom → 3 facilities ranked by trust on a map
- Each card shows trust score with confidence interval + per-field breakdown
- Click any field → MLflow trace panel reveals the exact source sentence in the original facility note
- One hospital is visibly demoted via Validator contradiction flag
- Genie Code accepts at least one judge-typed multi-attribute query live
- NGO Desert Dashboard renders India PIN map with toggleable specialty layers (dialysis, oncology, trauma)
- One PIN deep-click reveals "0 facilities within Xkm radius, population Y"
- Databricks App URL is `*.databricksapps.com`
- MLflow 3 Registry shows Extractor + Validator versioned with row-level traces

**Pitch quality:**
- Opens with the data problem ("10,000 messy records")
- Architecture diagram fits on one slide: Extractor ⇄ Validator → Trust Scorer → Gold → UI
- Human story hits the inverse-care-law and the dialysis-desert anecdote
- Closer line: *"We turned 10,000 messy records into a trust map you can click through to the source sentence."*

**Rubric self-score target:**
- 35% Discovery & Verification — two-agent independent doubt + per-field contradiction flags + prediction intervals
- 30% IDP Innovation — multi-attribute structured extraction over messy 10k with mixed-language fields
- 25% Social Impact — NGO Desert Dashboard with PIN-coded gap filtering
- 10% UX/Transparency — MLflow 3 click-to-source on every field

---

## 15. Comparison To Sibling Specs

This spec is one of three sibling proposals for the same hackathon (Challenge 03, same 4-person team, same 10k dataset). For side-by-side reading:

| | **This spec (Aarogya AI)** | `2026-04-25-healthcare-multiagent-design.md` (Tero) | `2026-04-25-healthcare-aarogyanet-react-swarm.md` (AarogyaNet) |
|---|---|---|---|
| **Killer** | Extractor + Validator → contradictions → trust score with CI | Verify-All-4 + atomic booking + outcome loop + reputation | Live agent reasoning panel + 3-agent ReAct + dead zones |
| **Posture** | Analytical (fix the data) | Operational (book the bed) | Demo-first (build to flow) |
| **Agents** | 2 (extractor, validator) + 1 orchestrator | 8+ in supervisor/sub-agent topology | 3 (Triage, Availability, Navigator) |
| **Live data** | None (batch pipeline) | IntakeAgent handshakes + outcome ping | Synthetic ±2 beds / 5 min stream |
| **Voice** | None | Tier-2 fallback (Fish Audio + OpenAI Realtime) | Browser Web Speech API |
| **NGO surface** | First-class (desert dashboard) | First-class (desert dashboard) | Dead Zone heatmap layer |
| **Scope risk** | Low (small contract surface) | High (8 components, 4-way atomic txn) | Medium (3 agents + live UI) |
