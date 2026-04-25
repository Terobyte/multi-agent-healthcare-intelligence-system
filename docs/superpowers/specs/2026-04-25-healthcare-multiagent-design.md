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

- **Stack:** UC function + mock 108/ABDM HTTP endpoints (no MCP layer needed — UC fn calls FastAPI mock directly)
- **Owner:** **Mubarak** (reassigned from Tero based on review findings — Mubarak's RAG/AI-TAX-REFORM background fits FHIR snippet generation + structured packet assembly)
- **Folder:** `mubarak/transfer/` (added to Mubarak's track)
- **Wraps:**
  - Mock 108 ambulance dispatch endpoint (returns ETA countdown)
  - Mock ABDM record packaging (returns FHIR snippet + PDF URL)
  - D2D handoff form generator
- **Input/Output:** see `contracts/schemas.py` (`TransferInput` / `TransferOutput`)

### 3.6 Voice MCP Server (Hybrid Stack)

- **Stack (revised after agent review):** FastAPI + WebSocket hosted as a **Databricks App** (Databricks Apps support FastAPI + WS — no external hosting needed).
  - **TTS:** Fish Audio WebSocket (Tero's existing engine in `~/Desktop/Projects/Active/ai_hack/fishaudio/`) — Hindi prompts pre-generated and cached at startup
  - **STT:** OpenAI `gpt-4o-audio` (replaces Deepgram per agent review — better on noisy phone audio, native Hindi)
  - **LLM + structured output:** OpenAI `gpt-4o` with function calling (parses transcript → `verified_p_bed` directly, no separate parser)
  - **Optional Phase 3:** Twilio Media Streams for real outbound phone call
- **Integration with Supervisor:** UC function calls Voice MCP HTTP endpoint directly (no MCP protocol — agent review flagged this as unverified for custom Python servers)
- **Owner:** Tero (TTS layer + FastAPI shell from existing engines), with Mubarak reviewing Hindi prompt content
- **Folder:** `tero/voice/`
- **Modes** (env var `VOICE_MODE`):
  - `mock` (default for demo) — pre-recorded audio + hardcoded JSON, never fails
  - `realtime` — live OpenAI loop, microphone in browser → Voice MCP → audio response
  - `twilio` (Phase 3 stretch) — real outbound phone call via Twilio
- **Trigger conditions** (set by Supervisor): `min(BedPredictor.confidence) < 0.7 OR last_sample_age > 2h OR patient_in_transit == true`
- **Demo theatre rule:** voice fires → on-screen `verifying` banner → confidence band tightens → ranking re-orders. Audio without on-screen change = wasted demo seconds.
- **Input/Output:** see `contracts/schemas.py` (`VoiceVerifyInput` / `VoiceOutput`). New fields after review: `original_p_bed`, `confidence_after_voice`, `mode_used`.

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

## 7. Team Mapping (revised after agent review — load-balanced)

| Person | Owns | Project Folder | Stack | Risk |
|---|---|---|---|---|
| **Tero** | Supervisor + Voice MCP + RouterAgent (Genie config) + integration + demo theatre + pitch coordination | `tero/supervisor/`, `tero/voice/`, `tero/router-config/` | Python, Mosaic AI Agent Bricks, Fish Audio, OpenAI Realtime, Genie | High — orchestrator + voice + integration |
| **Mubarak** (senior) | TriageAgent + **TransferCoordinator** (reassigned from Tero) + integration tests | `mubarak/triage/`, `mubarak/transfer/` | Python, Knowledge Assistant, Vector Search, UC functions, FHIR | Medium — Databricks ramp-up; load now balanced |
| **Mian / Danish** | BedPredictor + DLT pipeline + **stub gold table FIRST** to unblock everyone | `mian/predictor/`, `mian/dlt-pipeline/` | Python, MLflow Models-from-Code, sklearn, Lakeflow/DLT | Medium — critical path: stub-first unblocks team |
| **Arushi** | Databricks App (React) — Patient flow + Doctor copilot | `arushi/app/` | React + appkit SDK + Leaflet/Mapbox | Low — strong React shipping; just learning appkit |

**Key redistribution from review findings:**
- `TransferCoordinator` moved Tero → Mubarak (review flagged Tero at 150% load, Mubarak at 40%; FHIR + structured packet generation matches Mubarak's RAG profile)
- **Stub gold table comes FIRST** in Mian's track (review flagged DLT as serial bottleneck — Mian commits 50-row hardcoded gold table within first hour, full DLT runs in parallel afterwards)
- `Alert agent` (notifications/SMS) → folded into Databricks App as toast-level UI; not a separate sub-agent. Phase 3 stretch can wire real Twilio.

---

## 8. Build Order — 19-Hour Schedule (revised after agent review)

### H 0-1 — Provisioning + spikes (everyone)
- [ ] [Tero] Databricks workspace + UC perms for all 4 owners
- [ ] [Mian] **STUB gold table:** 50 hardcoded hospitals committed to Delta within first hour. **Unblocks Mubarak's Vector Search, Tero's Genie Space, Mubarak's Triage corpus indexing.**
- [ ] [Tero] hello-world Mosaic AI Supervisor spike
- [ ] [Mubarak] hello-world Knowledge Assistant spike
- [ ] [Arushi] appkit SDK hello-world Databricks App spike
- [ ] [Tero] commit `contracts/schemas.py` + all `*_output.json` mocks → unblocks parallel work

### H 1-7 — Phase 1: Foundation (parallel, no one blocked)
- [ ] [Mian] DLT pipeline real: bronze → silver → gold (replaces stub)
- [ ] [Mian] BedPredictor v1 history-only baseline → MLflow Models-from-Code → UC function
- [ ] [Mubarak] TriageAgent skeleton: Knowledge Assistant indexed over 5-10 symptom docs
- [ ] [Tero] Supervisor skeleton: reads mock JSONs from `contracts/`, returns aggregated `SupervisorResponse`
- [ ] [Tero] Voice MCP shell: FastAPI + WS + Fish Audio TTS pre-cached + mock mode
- [ ] [Tero] Genie Space configured over silver hospitals table + 5 example queries
- [ ] [Arushi] Patient flow page: input + map + 3 hospital cards from mock SupervisorResponse

**H 7 Phase 1 demo state:** *"Type 'fever, Lucknow' → 3 hospitals on map with bed predictions, all on Databricks Apps URL."*

### H 7-13 — Phase 2: Two Killers Light Up
- [ ] [Tero] Voice MCP realtime mode: OpenAI gpt-4o-audio (STT) + GPT-4o function calling (LLM/parse) + Fish Audio (TTS) wired
- [ ] [Tero] Confidence-trigger logic in Supervisor (`min(confidence) < 0.7 OR sample > 2h` → invoke Voice MCP)
- [ ] [Mubarak] TransferCoordinator: UC function + mock 108 endpoint + FHIR snippet generator
- [ ] [Arushi] Patient flow Voice theatre: `verifying` banner + confidence band tightening animation
- [ ] [Arushi] Doctor copilot page: sending hospital → 3 receivers + packet preview + ambulance ETA countdown
- [ ] [Mubarak] TriageAgent expanded: full corpus, urgency scoring, Hindi vocab
- [ ] [Mian] BedPredictor v2: ingest Voice MCP feedback as ground truth

**H 13 Phase 2 demo state:** Two killing features fully working.

### H 13-16 — Phase 3 (pick 2 Tier-1 + 1 Tier-2)
**Tier 1 (Databricks-native theatre — pick at least 2):**
- [ ] [Mian] MLflow Model Registry + Lakehouse Monitoring drift panel ready to click on stage
- [ ] [Tero/Arushi] Genie Space embedded in App — judge types "ICUs in Pune <30 min" live → SQL renders
- [ ] [Tero] Databricks App URL is `*.databricksapps.com` (sponsorship signal)

**Tier 2 (pick 1 max):**
- [ ] [Tero] LIVE OpenAI Realtime voice loop during demo (microphone in browser, not phone)
- [ ] [Mubarak] Bridge Doctor Mode (D2D shared screen with structured handoff)
- [ ] [Arushi] Ambulance ETA countdown with map icon animation

### H 16-18 — Integration + contract tests (everyone)
- [ ] Each owner runs `pytest contracts/test_my_output.py` — output matches Pydantic schema
- [ ] [Tero] swap mock JSONs in Supervisor → real sub-agent calls
- [ ] End-to-end test: Patient flow + Doctor flow against real backend
- [ ] [Mubarak] writes E2E integration test (his second responsibility)
- [ ] Demo theatre check: every second of demo something Databricks-native moves

### H 18-19 — Demo rehearsal + slides
- [ ] 3 full demo runs against real backend
- [ ] 1 demo run with Voice MCP forced to mock (fallback drill)
- [ ] [Arushi] submission package: README, demo video, Devpost writeup, GitHub polish
- [ ] Slide deck architecture diagram

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

## 10. Risks & Open Questions (revised after agent review)

| Risk | Severity | Mitigation |
|---|---|---|
| Mubarak no Databricks/MLflow evidence — now with bigger load (Triage + Transfer) | Medium | Pair with Mian on first MLflow checkin H 1-3; FHIR snippet generation simpler than full ABDM |
| ~~MCP protocol unverified~~ Voice MCP not actually MCP — it's UC fn → FastAPI HTTP | Resolved | Voice MCP exposes plain HTTP; UC function calls it directly. No MCP protocol layer needed. |
| Live OpenAI Realtime fails at demo (network, API outage) | High | `VOICE_MODE=mock` default + pre-recorded audio fallback in Voice MCP — never breaks demo |
| All 4 need Databricks workspace + UC perms | High | Tero provisions H 0; verify before everyone starts |
| appkit SDK is new — docs may be thin | Medium | Arushi H 0-1 spike — build hello-world before any real work |
| 10k records source format unknown — Mian's DLT depends on it | High | Mian H 0-1 sniff sample; **stub gold table H 1 unblocks team regardless** |
| Hindi prompt quality | Medium | Mubarak drafts Hindi corpus + reviews Voice prompts; Mian/Danish (Urdu native) cross-check |
| DLT pipeline serial bottleneck | High | **Resolved** by stub-first strategy: Mian commits 50-row hardcoded gold within H 1 → others unblocked |
| Tero overloaded (review found 150% load) | Medium | TransferCoordinator moved to Mubarak; Tero now ~110% (still high but manageable) |
| Integration day = first E2E test, 4-6h not realistic | High | **Contract tests in each folder from H 1** (`pytest contracts/test_my_output.py`) — validates JSON shape against Pydantic schema continuously, not just on integration day |

---

## 11a. Demo Script (second-by-second, 2 min)

**00:00-00:15** — Setup shot. Slide 1: "55M Indians pushed into poverty annually. 70% of population, 30% of beds." Architecture diagram visible (mirrors AiChemy, 4 sub-agents under Supervisor).

**00:15-00:35** — Patient flow opens in Databricks App (`*.databricksapps.com` URL visible in browser). Type «बुखार, लखनऊ» (fever, Lucknow). 3 hospitals render on map with confidence bands. **MLflow trace IDs visible in dev panel (left).**

**00:35-00:55** — One hospital shows confidence < 0.7. **Voice MCP fires.** Banner appears: "Verifying availability live...". TTS audio plays (Fish Audio, Hindi: «Kya bed khali hai?»). 5 seconds of mock-recorded response. Confidence band tightens visibly. Hospital ranking re-orders. **Vector Search top-k panel updates simultaneously.**

**00:55-01:15** — Switch to Doctor copilot view. Select "St. John's Hospital" as sending. 3 receiving hospitals appear with capability scores. Click "Generate referral" → FHIR snippet renders + PDF preview + ambulance ETA countdown ticking down. **Map shows ambulance icon moving.**

**01:15-01:35** — Click Genie Space embedded chat. Judge prompt: "Show me ICUs with ventilator capacity in Maharashtra under 30 minutes". SQL renders live. Table populates. **Lakehouse Monitoring drift panel visible in second tab.**

**01:35-01:55** — Architecture recap slide. 4 sub-agents named (Triage, BedPredictor, Router, TransferCoordinator) each labeled with their Databricks primitive (Knowledge Assistant, UC fn + MLflow, Genie Space, UC fn). Supervisor at top. MLflow + Vector Search + DLT visible underneath.

**01:55-02:00** — One-line close: "Voice predicts. Lakehouse remembers. Supervisor decides. All Databricks-native."

---

## 11b. Fallback Strategy

If anything fails on demo day, here's the swap order:

| Failure | Swap to | Setup before demo |
|---|---|---|
| Voice MCP realtime API unavailable | `VOICE_MODE=mock` (env var flip) — pre-recorded Hindi audio + hardcoded JSON | Pre-record audio H 16-18 |
| Genie Space query times out | Pre-recorded screen capture + slide overlay "captured live, week ago" | Record H 16-18 |
| Databricks App deploy down | Backup deploy on Vercel (hn5-kit base still works) — URL change but flow identical | Keep Vercel deploy alive H 16-18 |
| Supervisor crashes mid-demo | Mock SupervisorResponse JSON file → frontend reads from local instead | Have file on disk H 16-18 |
| MLflow lineage panel slow | Static screenshot in slide instead of live click | Take screenshot H 16-18 |

**Rule:** every "live" demo moment must have a pre-recorded version that's been tested. No moment is "either live or nothing."

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
