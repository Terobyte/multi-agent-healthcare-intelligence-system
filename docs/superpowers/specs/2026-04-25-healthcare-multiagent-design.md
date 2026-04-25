# Healthcare Multi-Agent Intelligence — Design Spec

> **Variant chosen:** AiChemy 1:1 Mirror (Supervisor Agent over 4 named sub-agents)
> **Deployment target:** Databricks-native (Databricks App via appkit React SDK + Mosaic AI Agent Framework + Unity Catalog + Lakeflow/DLT + MLflow + Genie + Vector Search)
> **Challenge:** Agentic Healthcare Maps (Bharat Bricks Hacks 2026 / Databricks-sponsored)
> **Last updated:** 2026-04-25

---

## 1. Executive Summary

A multi-agent healthcare intelligence system that turns 10,000 messy Indian hospital records into an operational brain. Two killing features stack on top of a 4-sub-agent architecture:

- **Killer A — Voice-Verified Prediction:** predict P(bed | hospital, t) from history; voice-verify only when patient is on the road AND confidence < 0.7. Fires 10× fewer staff calls than naive verification, 10× more accurate than ghost-bed dashboards.
- **Killer B — Inter-Facility Transfer Copilot:** when a doctor says "move them to a tertiary center," our agent ranks 3 receivers, packages records (FHIR + PDF), books ambulance, opens D2D handoff — all in one screen.

**Why Databricks-native:** Research finding from `research/08-databricks-challenge-priors.md` — judges score what's on screen (Lakehouse + Vector Search + MLflow + Genie + Apps). The pitch sells the human story; the demo sells the lakehouse. Both must be loud. AiChemy 1:1 mirror is recognised in 10 seconds by Databricks judges (4 ICs).

---

## 2. Architecture Diagram

```
                  ┌─────────────────────────────────────────┐
                  │  Databricks App (React via appkit SDK)   │
                  │  ├── Patient flow      (Killer A)        │
                  │  └── Doctor copilot    (Killer B)        │
                  └────────────────────┬────────────────────┘
                                       │ HTTPS
                                       ▼
                  ┌─────────────────────────────────────────┐
                  │  Supervisor Agent (Mosaic AI Agent       │
                  │  Bricks). Routes by intent. ACL-aware    │
                  │  via Unity Catalog.                      │
                  └──┬──────────┬──────────┬──────────┬─────┘
                     │          │          │          │
            ┌────────▼──┐ ┌─────▼────┐ ┌───▼─────┐ ┌──▼────────────┐
            │TriageAgent│ │BedPredict│ │ Router  │ │TransferCoord  │
            │(Knowledge │ │(UC fn →  │ │(Genie   │ │(UC fn + MCP   │
            │ Assistant │ │ MLflow   │ │ Space   │ │ for 108/ABDM) │
            │ symptom→  │ │ forecast │ │ over    │ │               │
            │ specialty)│ │ er)      │ │ Delta)  │ │               │
            └───────────┘ └────┬─────┘ └─────────┘ └───────┬───────┘
                               │                           │
                               │ confidence < 0.7?         │
                               └─────► Voice MCP ◄─────────┘
                                       (standalone Python,
                                        Fish Audio WS + STT/TTS,
                                        Hindi prompts, MCP server)
                                       │
                                       ▼ verified result
                              feeds back into BedPredictor

   ─────────── DATA PLANE ───────────
                  ┌─────────────────────────────────────────┐
                  │  Lakehouse (Delta + Unity Catalog)       │
                  │  bronze (raw 10k) → silver (norm) →      │
                  │  gold (routing-ready) via Lakeflow/DLT   │
                  │  + Vector Search (storage-optimized)     │
                  │  + Online Tables (live bed counts)       │
                  │  + MLflow Registry (BedPredictor)        │
                  │  + Lakehouse Monitoring (drift panel)    │
                  └─────────────────────────────────────────┘
```

---

## 3. Components

### 3.1 Supervisor Agent

- **Stack:** Mosaic AI Agent Framework (Agent Bricks Supervisor)
- **Owner:** Tero
- **Folder:** `agents/supervisor/`
- **Routes by intent:** patient triage requests → Triage+Predictor+Router; doctor transfer requests → Triage+Predictor+Router+TransferCoordinator
- **Confidence-trigger logic:** if min(BedPredictor.confidence) < 0.7 OR last_sample_age > 2h → invoke Voice MCP
- **Aggregates JSON outputs into killing-feature responses**
- **MLflow tracing** enabled — every trace visible in demo theatre

### 3.2 TriageAgent (sub-agent)

- **Stack:** Mosaic AI Knowledge Assistant + Vector Search (storage-optimized)
- **Owner:** Mubarak
- **Folder:** `agents/triage/`
- **Indexed corpus:** symptom → specialty mappings, hospital capability docs, Hindi/English medical terms
- **Input:** free-text symptoms (Hindi or English)
- **Output:**
  ```json
  {
    "specialty": "cardiology",
    "urgency": 3,
    "symptoms_parsed": ["chest pain", "shortness of breath"],
    "confidence": 0.84,
    "trace_id": "tr_abc123"
  }
  ```

### 3.3 BedPredictor (sub-agent)

- **Stack:** UC function calling MLflow-served forecaster (Models-from-Code)
- **Owner:** Mian (Danish)
- **Folder:** `agents/predictor/`
- **Model:** history-only baseline P(bed | hospital, time) for v1; later enriched by Voice MCP feedback
- **Registered in MLflow Model Registry under Unity Catalog**
- **Lakehouse Monitoring drift panel** wired up (demo theatre tier-1 signal)
- **Input:** specialty + city/district + timestamp
- **Output:**
  ```json
  {
    "predictions": [
      {
        "hospital_id": "h_3421",
        "p_bed": 0.72,
        "confidence": 0.65,
        "last_sample_age_min": 145
      }
    ],
    "model_version": "v3",
    "trace_id": "tr_xyz789"
  }
  ```

### 3.4 RouterAgent (sub-agent)

- **Stack:** Genie Space over hospitals Delta table (gold tier)
- **Owner:** Tero (configuration, not code)
- **Folder:** `agents/router/` (just config + SQL examples)
- **Demo wow:** judge types "ICUs with ventilator capacity in Maharashtra <30 min" into Genie box → SQL renders live → table populates
- **Input:** specialty + location + ranked hospital list from BedPredictor
- **Output:**
  ```json
  {
    "ranked": [
      {
        "hospital_id": "h_3421",
        "name": "AIIMS Lucknow",
        "travel_min": 18,
        "specialty_match": 0.91,
        "cost_estimate_inr": 12000,
        "non_medical_cost_inr": 4500
      }
    ],
    "genie_query_id": "gq_xyz"
  }
  ```

### 3.5 TransferCoordinator (sub-agent)

- **Stack:** UC function + MCP server for 108/ABDM mock
- **Owner:** Tero
- **Folder:** `agents/transfer/`
- **Wraps:**
  - Mock 108 ambulance dispatch endpoint (returns ETA countdown)
  - Mock ABDM record packaging (returns FHIR snippet + PDF URL)
  - D2D handoff form generator
- **Input:** sending_hospital_id + patient_summary + receiving_hospitals
- **Output:**
  ```json
  {
    "receiving_hospitals": [...],
    "referral_packet_url": "https://.../ref_123.pdf",
    "fhir_snippet": "{...}",
    "ambulance_eta_min": 14,
    "d2d_handoff_id": "d2d_456"
  }
  ```

### 3.6 Voice MCP Server

- **Stack:** Standalone Python (FastAPI), Fish Audio WebSocket + Deepgram STT + Hindi prompt scripts. Wrapped as MCP server, registered in Mosaic AI as managed MCP connector.
- **Owner:** Tero (lead) + Mian (Hindi/Urdu prompt content) + Mubarak (orchestration logic)
- **Folder:** `voice/` (separate repo or subdirectory)
- **Trigger conditions** (set by Supervisor): `confidence < 0.7 OR last_sample_age > 2h OR patient_in_transit == true`
- **15-second call** in vernacular, single yes/no/number question
- **Demo theatre rule:** voice fires; the screen reacts — confidence band must visibly tighten and ranking must re-order
- **Input:** hospital_id + question_template
- **Output:**
  ```json
  {
    "hospital_id": "h_3421",
    "verified_p_bed": 0.95,
    "verified_at": "2026-04-25T14:23:11Z",
    "raw_transcript": "Haan, do bed khali hain",
    "audio_url": "https://.../call_789.wav"
  }
  ```

### 3.7 Databricks App (UI)

- **Stack:** React + appkit SDK (Databricks-native React framework)
- **Owner:** Arushi
- **Folder:** `app/`
- **Reuses from `hn5-kit`:** Map widget (Leaflet), card components, ChatPanel pattern, layout grid
- **Two surfaces:**
  - **Patient flow (Killer A):** input box (Hindi/English) → 3 hospitals on map → animated "verifying live" banner when Voice MCP fires → confidence bands re-tighten visibly → cost-truth card on each result
  - **Doctor copilot (Killer B):** select sending hospital → 3 receiving recommendations → referral packet preview → ambulance ETA countdown → D2D handoff form
- **Genie Space embedded** in dashboard (Phase 3) — judge types live, SQL renders

### 3.8 Data Plane

- **Lakeflow / DLT** medallion pipeline:
  - **Bronze:** raw 10k hospital records (whatever format — CSV, JSON, scraped HTML)
  - **Silver:** normalized addresses (geocoded), deduped, specialty taxonomy mapped
  - **Gold:** routing-ready (joined with district pop, road network for travel-time estimates)
- **Vector Search (storage-optimized, GA):** indexes hospital descriptions + symptom→specialty corpus
- **Online Tables:** low-latency replicas of `bed_counts` for serving
- **MLflow Registry:** BedPredictor versioned, lineage visible in demo
- **Lakehouse Monitoring:** drift panel for predictor quality over time
- **Unity Catalog:** governance + ACLs across all of the above

---

## 4. Data Flow — Killer A (Voice-Verified Prediction)

```
[Patient via Databricks App] types "बुखार, लखनऊ" (fever, Lucknow)
    │
    ▼
[Supervisor Agent] receives intent: triage_route
    │
    ├─▶ TriageAgent  ──▶ {specialty: "general medicine", urgency: 2}
    │
    ├─▶ BedPredictor ──▶ 3 hospitals + P(bed) + confidence
    │       │
    │       └─ if min(confidence) < 0.7 OR sample > 2h:
    │            │
    │            └─▶ Voice MCP fires
    │                  │
    │                  ├─ Databricks App shows "verifying live" banner ◄── DEMO THEATRE
    │                  ├─ Fish Audio WS dials hospital → Hindi yes/no question
    │                  ├─ STT parses response → verified_p_bed
    │                  └─ feeds back to BedPredictor → confidence updates
    │                       │
    │                       └─ Databricks App re-renders confidence band TIGHTENING ◄── DEMO THEATRE
    │
    ├─▶ RouterAgent (Genie) ──▶ re-rank by P × travel × specialty × cost
    │
    └─▶ Supervisor returns aggregated payload
          │
          ▼
[Databricks App] renders 3 hospitals on map + cost-truth card per hospital
```

---

## 5. Data Flow — Killer B (Transfer Copilot)

```
[Doctor via Databricks App] selects "Transfer patient from St. John's"
    │
    ▼
[Supervisor Agent] receives intent: transfer_coordinate
    │
    ├─▶ TriageAgent      ──▶ tertiary specialty needed (cardiothoracic surgery)
    │
    ├─▶ BedPredictor     ──▶ 3 candidate receivers + P(bed) + confidence
    │
    ├─▶ RouterAgent      ──▶ ranked by capability + travel + bed
    │
    └─▶ TransferCoordinator
          │
          ├─ generates FHIR snippet + PDF referral packet
          ├─ books ambulance (mock 108 MCP) → ETA countdown ◄── DEMO THEATRE
          ├─ opens D2D handoff form
          └─ returns aggregated packet
                │
                ▼
[Databricks App] renders: 3 receivers card + packet preview + map with ambulance icon moving + D2D form
```

---

## 6. Integration Contracts (the "4 independent projects" enabler)

Each sub-agent owner emits a fixed JSON shape. Supervisor parses, validates with Pydantic. **Anyone can build their sub-agent without waiting for any other.**

```
TriageAgent.output  →  { specialty, urgency, symptoms_parsed, confidence, trace_id }
BedPredictor.output →  { predictions[{hospital_id, p_bed, confidence, last_sample_age_min}], model_version, trace_id }
RouterAgent.output  →  { ranked[{hospital_id, name, travel_min, specialty_match, cost_estimate_inr, non_medical_cost_inr}], genie_query_id }
TransferCoord.output→  { receiving_hospitals, referral_packet_url, fhir_snippet, ambulance_eta_min, d2d_handoff_id }
VoiceMCP.output     →  { hospital_id, verified_p_bed, verified_at, raw_transcript, audio_url }
```

**Integration day** (last 4-6 hours):
1. Supervisor stub already exists with mocked sub-agent calls
2. Each owner replaces their mock with real implementation by emitting matching JSON
3. End-to-end test on demo dataset
4. Demo theatre rehearsal

---

## 7. Team Mapping

| Person | Owns | Project Folder | Stack | Risk |
|---|---|---|---|---|
| **Tero** (lead) | Supervisor + TransferCoordinator + Voice MCP + RouterAgent (Genie config) + integration + demo theatre + pitch coordination | `agents/supervisor/`, `agents/transfer/`, `agents/router/`, `voice/` | Python, MCP, Mosaic AI Agent Bricks, Fish Audio, Genie | High — owns 3 components + integration |
| **Mubarak** (senior) | TriageAgent (Knowledge Assistant) | `agents/triage/` | Python, Mosaic AI Knowledge Assistant, Vector Search | Medium — Databricks ramp-up needed |
| **Mian / Danish** (junior ML) | BedPredictor + DLT ingest pipeline (bronze/silver/gold) | `agents/predictor/`, `data/dlt/` | Python, MLflow Models-from-Code, sklearn, Lakeflow/DLT | Medium — pair with Tero on first MLflow checkin |
| **Arushi** (UI) | Databricks App (React) — Patient flow + Doctor copilot | `app/` | React + appkit SDK + Leaflet + Mapbox | Low — strong React shipping; just learning appkit |

`Alert agent` (notifications/SMS) → folded into Databricks App as toast-level UI; not a separate sub-agent. Phase 3 stretch can wire real Twilio.

---

## 8. Build Order (Phased, mirrors `ideas/killing-features.md`)

### Phase 1 — Foundation (parallel, each person works in isolation)

- [ ] [Mian] DLT pipeline: 10k records → bronze → silver (geocoded, deduped) → gold
- [ ] [Mubarak] TriageAgent skeleton: Knowledge Assistant indexed over 5-10 sample symptom docs
- [ ] [Mian] BedPredictor v1 history-only baseline → MLflow Registry
- [ ] [Tero] Supervisor skeleton: hardcoded request → calls all 3 sub-agents → returns JSON
- [ ] [Arushi] Databricks App: input box + 3 hospital cards rendering mock data
- [ ] [Tero] Genie Space configured over silver hospitals table + 5 example queries seeded
- [ ] [Tero] Vector Search index built over hospital description corpus

**Phase 1 demo state:** *"Type 'fever, Lucknow' → see 3 hospitals with confidence-banded bed predictions on a map, all running on Databricks Apps."*

### Phase 2 — Two Killers Light Up

- [ ] [Tero] Voice MCP: Fish Audio WS + Hindi prompt + STT/TTS, wrapped as MCP server
- [ ] [Tero] Confidence-trigger logic in Supervisor: confidence<0.7 OR sample>2h fires Voice
- [ ] [Tero] TransferCoordinator UC function + 108 MCP mock + FHIR snippet generator
- [ ] [Arushi] Patient flow with animated "verifying live" banner + confidence band tightening
- [ ] [Arushi] Doctor copilot screen for Killer B
- [ ] [Mubarak] TriageAgent expanded: full corpus, urgency scoring, Hindi vocab
- [ ] [Mian] BedPredictor v2: feeds back Voice MCP verified samples as ground truth

**Phase 2 demo state:** Two killing features fully working with live demo theatre.

### Phase 3 — Crazy Wow (pick 3, at least 2 from Tier 1)

**Tier 1 (Databricks-native theatre):**
- [ ] [Mian] MLflow Model Registry + Lakehouse Monitoring drift panel — click "lineage" → click "drift dashboard" on stage
- [ ] [Tero/Arushi] Genie Space embedded in App — judge types "ICUs in Pune <30 min" live → SQL renders → table populates
- [ ] [Tero] Databricks App is the deployment vehicle — URL is `*.databricksapps.com`, no Vercel/Replit

**Tier 2 (Voice + transfer flows):**
- [ ] LIVE outbound voice call during demo (only if visualized on screen)
- [ ] Bridge Doctor Mode (D2D shared screen)
- [ ] Ambulance auto-dispatch with countdown

**Tier 3 (Distribution):**
- [ ] SMS/IVR fallback via Twilio India
- [ ] ASHA Co-Pilot tablet view
- [ ] Crowdsourced ground-truth feedback loop

---

## 9. Demo Theatre Discipline

**Rule (per `ideas/killing-features.md`):** on every second of the demo, something Databricks-native must be moving on screen.

For each killer firing, this checklist must be satisfied:
- [ ] Supervisor Agent trace ID visible in dev panel
- [ ] MLflow trace events live-streaming
- [ ] Genie SQL renders in embedded box (Phase 3)
- [ ] When Voice MCP fires, BedPredictor confidence band visibly tightens
- [ ] When Voice MCP fires, hospital ranking re-orders animation
- [ ] Lakehouse Monitoring drift bars update during demo (Phase 3)
- [ ] Vector Search top-k visible somewhere on screen

**Voice without on-screen change = wasted demo seconds.** This is the single most important demo-day discipline.

---

## 10. Risks & Open Questions

| Risk | Severity | Mitigation |
|---|---|---|
| Mubarak no Databricks/MLflow evidence | Medium | Pair with Mian on first MLflow checkin Phase 1 |
| Voice MCP wrapping protocol not verified for custom Python servers | High | Tero spike day -1: confirm MCP server registration in Mosaic AI |
| All 4 need Databricks workspace + UC perms | High | Tero owns provisioning hour 0; verify access before kickoff |
| appkit SDK is new (2025-2026) — docs may be thin | Medium | Arushi spike day -1: build hello-world Databricks App with appkit |
| 10k records source format unknown | High | Mian + Tero spike day -1: load sample, sniff schema, draft DLT bronze |
| Demo deadline unclear at design time | High | Tero confirms hackathon date with team before phase 1 starts |
| Hindi prompt quality for Voice MCP | Medium | Mian/Danish drafts Hindi/Urdu prompts; Mubarak review |

---

## 11. Out of Scope

- Real ABDM API integration (mock only)
- Real 108 dispatch (mock only)
- HMIS integration (out — covered in `research/03-bed-dashboards-postmortem.md` as known dead-end)
- Multi-language beyond Hindi (Bhojpuri/Marathi/Tamil/Bengali deferred to Phase 3 stretch)
- Mobile-native apps (Databricks App is web-only for hackathon)
- Production-grade auth (Databricks SSO is enough for demo)
- Long-term storage of voice recordings (delete after demo)

---

## 12. Success Criteria

**Demo-day pass:**
- Patient types Hindi symptom → 3 hospitals appear on map with bed predictions
- Voice MCP fires for one of those hospitals → confidence band tightens visibly
- Doctor switches to copilot view → selects sending hospital → receives 3 receivers + referral packet + ambulance ETA
- Databricks App URL is `*.databricksapps.com`
- MLflow Registry shows BedPredictor versioned
- Genie Space accepts at least one judge-typed query live

**Pitch quality:**
- Architecture diagram in slide deck shows 4 named sub-agents under Supervisor (mirrors AiChemy)
- Human story hits the 55M-into-poverty + Inverse-Care-Law beats
- Demo screen never goes static; Databricks-native primitive always moving
