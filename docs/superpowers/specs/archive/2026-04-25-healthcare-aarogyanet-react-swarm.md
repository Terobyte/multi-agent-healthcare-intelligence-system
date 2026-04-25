# AarogyaNet — ReAct Multi-Agent Swarm Spec

> **Approach:** Three specialised agents (Triage → Availability → Navigator) in a ReAct tool-calling loop, with a live agent reasoning panel and a synthetic ±2-beds-per-5-min stream that makes the demo feel alive
> **Source:** Teammate battle plan (`AarogyaNet_BattlePlan.pdf`, 2026-04-25) — friend 2's proposed path
> **Deployment target:** Databricks medallion pipeline + OpenAI/LLM orchestration + map-first React frontend
> **Challenge:** Serving A Nation — Building Agentic Healthcare Maps for 1.4 Billion Lives (Challenge 03, see `docs/challenge-brief.md`)
> **Last updated:** 2026-04-25

---

## 1. Executive Summary

> *"You describe symptoms in any language. We find care that's actually available — and book your transport. In under 60 seconds."*

A 4-layer stack engineered for **demo theatre over feature completeness**. Three specialised agents reason in a ReAct loop while a live panel on screen shows them thinking — judges *watch the AI work*. A synthetic update stream (±2 beds every 5 min) makes the map feel like a live operational system. A Dead Zone heatmap layer reveals coverage gaps at a glance.

**Three architectural choices that define this approach:**

1. **The agent reasoning panel is the hero.** Most submissions will hide their agents behind a chat output. We expose the chain-of-thought live: "Triage Agent → Cardiology + Pulmonology, urgency HIGH" → "Availability Agent → querying Gold table, 247 candidates → top 3 by distance × traffic × availability × rating" → "Navigator Agent → Ola deeplink generated." Judges see the agentic AI as it happens.
2. **Synthetic live stream beats real APIs.** Real Indian hospital APIs do not exist at scale. We acknowledge that and run a script that updates bed counts in Delta every 5 minutes (±2 beds, occasional ICU-full flags). Be honest in the pitch: *"In production this connects to IVR systems. In our demo we simulate the pipeline to show the architecture."* Judges respect this.
3. **One great screen, not five mediocre ones.** Map of India (Maharashtra or UP — good facility density) with color-coded pins. Floating chat. Live agent panel. 3 facility cards with ETA + transport button. That is the entire surface. No second dashboard, no second flow.

**The one rule, lifted verbatim from the source:**

> *DO NOT TRY TO BUILD EVERYTHING. Judges are not using your product — they are evaluating your architecture, your demo, and your story. A polished demo of 70% of this plan beats a buggy demo of 100% every single time.*

**Why this matches the brief:**

| Brief weight | Component covering it |
|---|---|
| **35% Discovery & Verification** | ReAct agent loop visible end-to-end + per-card confidence scores |
| **30% IDP Innovation** | Data Cleaning Agent (LLM function calls) over 10k mixed Hindi/English / PDF / CSV inputs → Bronze→Silver→Gold |
| **25% Social Impact** | Dead Zone Map Layer auto-rendered from the same pipeline |
| **10% UX/Transparency** | Live agent reasoning panel + confidence scores ("87% confident — last verified 2 hours ago") |

**Why this prize stack:** Databricks Grand Prize anchors on the medallion pipeline (shown live: raw garbage in, clean intelligence out). $3K OpenAI API credits cover the agent core. India real-world impact is the third axis. Three boxes checked, one system.

---

## 2. Architecture Diagram — 4-Layer Stack

```
   ╔═══════════════════════════════════════════════════════════════╗
   ║  LAYER 4 — FRONTEND: THE DEMO MOMENT                          ║
   ║                                                                ║
   ║  ┌────────────────────────┐  ┌──────────────────────────┐    ║
   ║  │  Map of India          │  │  Floating Chat            │    ║
   ║  │  (Maharashtra / UP)    │  │  + LIVE Agent Reasoning   │    ║
   ║  │  green/yellow/red pins │  │    Panel — judges watch   │    ║
   ║  │  Dead Zone heatmap     │  │    the AI think           │    ║
   ║  │  toggleable            │  └──────────────────────────┘    ║
   ║  └────────────────────────┘                                   ║
   ║  ┌─────────────────────────────────────────────────────────┐  ║
   ║  │ 3 facility cards: ETA, distance, specialists, transport │  ║
   ║  │ button (Ola/Uber deeplink), confidence score            │  ║
   ║  └─────────────────────────────────────────────────────────┘  ║
   ╚═══════════════════════════════════════════════════════════════╝
                    ▲                          │
                    │ REST /api/recommend      │ user input
                    │                          ▼
   ╔═══════════════════════════════════════════════════════════════╗
   ║  LAYER 2 — AGENT ORCHESTRATION CORE (ReAct loop)              ║
   ║                                                                ║
   ║   ┌───────────────┐   ┌─────────────────┐   ┌──────────────┐  ║
   ║   │ Triage Agent  │──▶│ Availability    │──▶│ Navigator    │  ║
   ║   │ symptoms →    │   │ Agent           │   │ Agent        │  ║
   ║   │ specialty +   │   │ Gold query +    │   │ Ola/Uber +   │  ║
   ║   │ urgency       │   │ score formula   │   │ ambulance #  │  ║
   ║   └───────────────┘   └────────┬────────┘   └──────────────┘  ║
   ║                                │                              ║
   ║   Each step streams to ───────┘  → Layer 4 reasoning panel   ║
   ╚═══════════════════════════════════════════════════════════════╝
                                    │
                                    ▼ reads
   ╔═══════════════════════════════════════════════════════════════╗
   ║  LAYER 1 — DATA INTELLIGENCE PIPELINE (Databricks)            ║
   ║                                                                ║
   ║   raw 10k (XLSX/CSV/PDF, mixed Hindi-English, dupes, missing  ║
   ║   pincodes)                                                    ║
   ║       │                                                        ║
   ║       ▼                                                        ║
   ║   ┌───────────────────────────────────────────────────────┐   ║
   ║   │ Bronze → Silver → Gold (Delta Live Tables)             │   ║
   ║   │  • Data Cleaning Agent: standardize names, geocode     │   ║
   ║   │    fuzzy addresses, extract bed counts from text,      │   ║
   ║   │    resolve duplicates                                   │   ║
   ║   │  • LLM function calls inline in DLT                    │   ║
   ║   └───────────────────────────────────────────────────────┘   ║
   ╚═══════════════════════════════════════════════════════════════╝
                                    ▲
                                    │ writes every 5 min
   ╔═══════════════════════════════════════════════════════════════╗
   ║  LAYER 3 — LIVE VERIFICATION HOOK (Synthetic stream)          ║
   ║                                                                ║
   ║   updater.py:  every 5 min, pick N rows in Gold,              ║
   ║                bed_count ± random(-2,+2),                     ║
   ║                occasional ICU-full flag                       ║
   ║                                                                ║
   ║   "In production: IVR. In demo: synthetic. Judges respect    ║
   ║    the honesty." — pitch line lifted from source              ║
   ╚═══════════════════════════════════════════════════════════════╝
```

---

## 3. Components

### 3.1 Layer 1 — Data Cleaning Agent (Bronze → Silver → Gold)

- **Stack:** Databricks Delta Live Tables + Model Serving + LLM function calls
- **Owner:** Danish (DLT pipeline lead)
- **Folder:** `mian/dlt-pipeline/`
- **What it does:**
  - **Bronze:** ingest 10k raw records (mixed XLSX, CSV, PDF). Apply Virtue Foundation pydantic schema for column mapping. Keep rows with missing critical fields, flag them.
  - **Silver:** Data Cleaning Agent runs LLM function calls per row to:
    - Standardize facility names (e.g., "Apollo Hosp." / "Apollo Hospital Limited" → canonical)
    - Geocode fuzzy addresses (Hindi-English mixed → PIN code)
    - Extract bed counts from unstructured text ("25-bed ICU + 12 general" → `icu_beds=25, general_beds=12`)
    - Resolve duplicates
  - **Gold:** clean, queryable, ready for the agent core. Shape matches Availability Agent's expected schema.
- **Demo value:** show this LIVE. Slide on the side: "Raw garbage in, clean intelligence out." This is the Databricks Grand Prize anchor — the medallion pipeline running on stage.

### 3.2 Layer 2 — Triage Agent

- **Stack:** OpenAI GPT-4o (function calling) — first agent in the ReAct loop
- **Owner:** Mubarak (agent expertise)
- **Folder:** `mubarak/triage/`
- **Input:** free-text symptoms (Hindi or English, transcribed if voice)
- **Output:** specialty (or list) + urgency band (LOW/MED/HIGH)
- **Example:** *"my father can't breathe, feet swollen"* → `{specialties: [cardiology, pulmonology], urgency: HIGH, reasoning_trace: "swollen feet + dyspnea suggest CHF — cardiology primary, pulmonology secondary"}`
- **Streaming:** every reasoning token streamed to the frontend reasoning panel as it generates.

### 3.3 Layer 2 — Availability Agent

- **Stack:** GPT-4o function calling + Databricks SQL over Gold + scoring formula
- **Owner:** Mubarak (lead) + Danish (SQL/scoring)
- **Folder:** `mubarak/availability/`
- **What it does:**
  - Receives `(specialties, urgency, user_location)` from Triage
  - Queries Gold table for facilities matching specialty within a radius
  - Scores each candidate: `score = w1·distance + w2·traffic + w3·availability + w4·rating`
  - Returns top 3 (or fewer) with reasoning trace
- **Streaming:** "querying Gold table... 247 candidates... applying score formula... top 3 selected" — visible in the panel.
- **Output:**
  ```json
  {
    "candidates": [
      {"hospital_id": "h_3421", "score": 0.91, "distance_km": 4.2, "availability": 0.82, "rating": 4.3},
      {"hospital_id": "h_8812", "score": 0.86, "distance_km": 7.1, "availability": 0.74, "rating": 4.5},
      {"hospital_id": "h_2145", "score": 0.78, "distance_km": 12.4, "availability": 0.91, "rating": 3.9}
    ],
    "reasoning_trace": "..."
  }
  ```

### 3.4 Layer 2 — Navigator Agent

- **Stack:** GPT-4o function calling + deeplink builders + ambulance number lookup
- **Owner:** Tero
- **Folder:** `tero/navigator/`
- **What it does:** for each top candidate, generate:
  - Ola deeplink: `olacabs://...` with destination pre-filled
  - Uber deeplink: `uber://...`
  - For HIGH urgency: ambulance number (108 in most states, regional variants)
- **Output appended to each facility card on the frontend.**

### 3.5 Layer 3 — Synthetic Live Stream

- **Stack:** Python script + Delta append, runs as Databricks job every 5 min
- **Owner:** Tero (script) + Danish (Delta plumbing)
- **Folder:** `tero/sim-stream/`
- **What it does:**
  - Picks ~30 random rows from Gold
  - For each: `bed_count = max(0, bed_count + randint(-2, +2))`
  - 5% chance: flip `icu_full = True`
  - Appends update row; Gold materialized view recomputes; map repaints
- **Demo value:** map pins shift color (green → yellow → red) live during the demo. ICU-full flag pops up. Judges see motion.
- **Pitch line:** *"In production this connects to IVR systems. In our demo we simulate the pipeline to show the architecture."* Honesty is the whole strategy.

### 3.6 Layer 4 — Map UI

- **Stack:** React + Leaflet.js (or Mapbox if performant) + WebSocket for live updates
- **Owner:** Arushi
- **Folder:** `arushi/app/`
- **Hero view:**
  - Map of India focused on Maharashtra or UP (good facility density for demo density)
  - Color-coded pins: green (high availability), yellow (medium), red (low/full)
  - Dead Zone heatmap layer (toggleable)
- **Side panel:**
  - Floating chat input (text or browser Web Speech API for voice)
  - Live Agent Reasoning Panel (streams from Layer 2)
- **Bottom:** 3 facility cards with ETA, distance, specialists, transport button, confidence score.

### 3.7 Layer 4 — Live Agent Reasoning Panel

- **Stack:** SSE or WebSocket from Layer 2 → React component
- **Owner:** Arushi (UI) + Tero (streaming wiring)
- **Folder:** `arushi/reasoning-panel/`
- **What it shows:** every reasoning token from each agent as it generates, labeled by agent ("🩺 Triage: ...", "🏥 Availability: ...", "🚗 Navigator: ...").
- **This is the killer.** No other team will surface chain-of-thought this prominently. Watch carefully: judges' eyes move to motion. Make sure something is moving here for every demo second.

### 3.8 Frontend — Confidence Scores

- **Stack:** read directly from Gold (last_verified_at + extraction_confidence) + render as one line per card
- **Owner:** Arushi
- **Format:** *"87% confident — last verified 2 hours ago"*
- **Why it matters:** the brainstorm explicitly calls out "shows your system knows what it doesn't know" — this is the technical-honesty signal that lands with ML judges.

### 3.9 Frontend — Dead Zone Map Layer

- **Stack:** SQL view over Gold grouping by PIN × specialty + color-coded geo overlay
- **Owner:** Danish (aggregation) + Arushi (overlay)
- **Folder:** `mian/dead-zones/`, `arushi/dead-zone-overlay/`
- **What it does:** when the pipeline runs, auto-identify districts with zero or critically low coverage. Render as heatmap toggle.
- **Demo value:** judges see the **problem and the solution simultaneously** on the same map.

### 3.10 Multilingual Voice Input (the +15-min addition)

- **Stack:** browser Web Speech API (free, native) — fallback to OpenAI Whisper if Web Speech misfires on Hindi
- **Owner:** Arushi (frontend) + Mubarak (Hindi prompt vetting)
- **Folder:** `arushi/voice-input/`
- **Why it earns its keep:** "India context demands this." Source verbatim.
- **Demo:** click mic, speak Hindi, transcript appears in chat, agent processes. Total user-facing latency budget: <2s.

### 3.11 WhatsApp Integration (optional, hours 18-20)

- **Stack:** Twilio WhatsApp sandbox + webhook to Layer 2
- **Owner:** Tero
- **Folder:** `tero/whatsapp/`
- **What it does:** user sends symptom message to a WhatsApp number → agent responds with top 3 facilities + transport links.
- **Why it matters (and why it is optional):** "Rural India is on WhatsApp, not web apps. Even a basic working demo is a massive differentiator." But the frontend is the demo hero — don't sacrifice it for this.

---

## 4. Data Flow — The Core Loop (User → Agents → Cards)

```
[User opens Databricks App]
    │
    ▼
[Mic icon]  user speaks Hindi: «मेरे पिताजी को सांस नहीं आ रही, पैर सूज गए हैं»
    │  (Web Speech API) → transcript appears in chat
    │
    ▼
[Triage Agent]
    │  REASONING PANEL: "🩺 Symptoms: dyspnea + bilateral pedal edema"
    │  REASONING PANEL: "🩺 Hypothesis: congestive heart failure"
    │  REASONING PANEL: "🩺 Specialty primary: cardiology, secondary: pulmonology"
    │  REASONING PANEL: "🩺 Urgency: HIGH"
    │
    ├─▶ output: {specialties: [cardiology, pulmonology], urgency: HIGH}
    │
    ▼
[Availability Agent]
    │  REASONING PANEL: "🏥 Querying Gold table: cardiology + pulmonology, radius 30km"
    │  REASONING PANEL: "🏥 247 candidates returned"
    │  REASONING PANEL: "🏥 Scoring: 0.4·distance + 0.2·traffic + 0.3·availability + 0.1·rating"
    │  REASONING PANEL: "🏥 Top 3 selected"
    │
    ├─▶ output: 3 ranked facilities with scores + reasoning
    │
    ▼
[Navigator Agent]
    │  REASONING PANEL: "🚗 HIGH urgency detected → fetching ambulance number"
    │  REASONING PANEL: "🚗 District ambulance: 108 (Maharashtra)"
    │  REASONING PANEL: "🚗 Generating Ola + Uber deeplinks for non-critical fallback"
    │
    ├─▶ output: deeplinks + ambulance # appended to each card
    │
    ▼
[Frontend renders 3 cards]
    │
    │  Card 1: Apollo Mumbai — 4.2km, 18min ETA, Cardiology + Pulmonology
    │          confidence 91% — last verified 12 min ago
    │          [Call ambulance 108]  [Ola]  [Uber]
    │
    │  Card 2: Hinduja — 7.1km, 24min ETA
    │          confidence 86% — last verified 8 min ago
    │          [Call ambulance 108]  [Ola]  [Uber]
    │
    │  Card 3: Lilavati — 12.4km, 31min ETA
    │          confidence 78% — last verified 2 hr ago  ⚠ stale
    │          [Call ambulance 108]  [Ola]  [Uber]
    │
    ▼
[Map] pins highlighted, ETA arcs drawn, transport button focused
```

---

## 5. Data Flow — Live Stream (Background, Always Running)

```
[updater.py]  scheduled every 5 min
    │
    ▼
[For 30 random rows in Gold]
    │  bed_count = max(0, bed_count + randint(-2, +2))
    │  if rand() < 0.05: icu_full = True
    │
    ▼
[Append to Delta] Gold materialized view recomputes
    │
    ▼
[WebSocket broadcast] frontend receives update
    │
    ▼
[Map] affected pin shifts color (green → yellow → red)
[Card] if currently shown, confidence + last_verified_at updates live
```

**Visible demo move:** during the pitch, the live stream's next tick fires while judges watch — a yellow pin turns red mid-presentation. *"And there it is — bed count just dropped at Hospital X. The system knows immediately."*

---

## 6. Integration Contracts

Each agent emits a fixed JSON shape. Pydantic-validated. **VF Schema is the base** (`from contracts.schemas import ...`).

```
TriageAgent.output       → { specialties[], urgency, reasoning_trace, trace_id }
AvailabilityAgent.output → { candidates[{hospital_id, score, distance_km, eta_min, availability, rating, confidence, last_verified_at}], reasoning_trace, trace_id }
NavigatorAgent.output    → { per_hospital{ola_url, uber_url, ambulance_number?}, reasoning_trace, trace_id }
DataCleaner.output       → Gold row with {hospital_id, name_canonical, pin, lat, lon, specialties[], beds{...}, last_verified_at, confidence}
LiveStream.event         → { hospital_id, beds_delta, icu_full, ts }
```

**Streaming contract** (the panel-to-agent wiring):
```
SSE event: {agent: "triage"|"availability"|"navigator", token: "...", trace_id}
```

**Integration day** (hours 16-20, "All" in the source):
1. Each backend owner exposes their agent behind a REST endpoint (no console-only demos)
2. Frontend wires SSE for reasoning panel
3. End-to-end smoke test: Hindi voice → 3 cards rendered with deeplinks, panel populated
4. Bug triage

---

## 7. Team Mapping

The source PDF uses anonymous roles ("Backend 1", "Backend 2", "Frontend", "1 person"). We map them to the actual 4-person team. The mapping reflects each person's strengths from the existing multi-agent design spec.

| Person | Role in source | Owns | Folder | Stack |
|---|---|---|---|---|
| **Tero** | Backend 1 (pipeline + sim stream) shared with Danish; Navigator Agent; integration; pitch | DLT pipeline plumbing + Synthetic Live Stream + Navigator Agent + WhatsApp (optional) + integration + demo theatre + pitch | `tero/navigator/`, `tero/sim-stream/`, `tero/whatsapp/` | Python, Databricks Jobs, OpenAI function calling, Twilio |
| **Mubarak** | Backend 2 (agent core) | Triage Agent + Availability Agent (lead) + Hindi prompt content | `mubarak/triage/`, `mubarak/availability/` | OpenAI GPT-4o function calling, Databricks SQL, ReAct |
| **Danish** | Backend 1 (Databricks pipeline) | Bronze→Silver→Gold DLT + Data Cleaning Agent (LLM function calls in DLT) + Dead Zone aggregation + Availability Agent SQL pairing | `mian/dlt-pipeline/`, `mian/dead-zones/` | Lakeflow/DLT, Databricks Model Serving, geocoding |
| **Arushi** | Frontend (the demo moment) | Map + chat + Live Agent Reasoning Panel + facility cards + Dead Zone overlay + voice input | `arushi/app/`, `arushi/reasoning-panel/`, `arushi/dead-zone-overlay/`, `arushi/voice-input/` | React, Leaflet/Mapbox, SSE/WebSocket, Web Speech API |

**Notes:**
- Frontend load is heaviest here — the demo *is* the frontend. Arushi gets the spotlight component.
- Tero owns the synthetic stream because it touches both Databricks (writes Delta) and demo theatre (timing the live tick during the pitch).
- The PDF says "1 person" for the pitch deck (hours 20-22). That is Tero — pitch is part of his existing scope.

---

## 8. Hour-by-Hour War Plan (24 hours)

The PDF specifies the schedule exactly. Reproduced below with owner assignments.

### H 0-2 — All hands: alignment + repo + raw data ready
- [ ] [Tero] Databricks workspace + UC perms for all 4
- [ ] [Tero] **Validate Free Edition supports**: DLT, Model Serving, Vector Search. Fall back if anything paid-only.
- [ ] [All] Architecture alignment — agree the demo flow now, never deviate
- [ ] [Tero] Repo scaffold, `contracts/schemas.py` from VF schema
- [ ] [Danish] Raw 10k loaded into Bronze — the "before" state ready to showcase as the opening hook

### H 2-8 — Backend split
- [ ] [Danish] DLT pipeline Bronze→Silver→Gold with LLM-based Data Cleaning Agent
- [ ] [Mubarak] Triage Agent: GPT-4o function calling, symptom → specialty + urgency
- [ ] [Mubarak] Availability Agent: tool-calling loop over Gold, scoring formula
- [ ] [Tero] Navigator Agent: deeplink builders + ambulance number lookup table

### H 8-12 — Backend 1 stream + REST
- [ ] [Tero] Synthetic update stream (±2 beds every 5 min, 5% ICU-full flags)
- [ ] [Tero] REST API endpoints exposing each agent (no console demos)
- [ ] [Mubarak/Danish] continue agent polish in parallel

### H 8-16 — Frontend
- [ ] [Arushi] Map UI (Leaflet) with color-coded pins
- [ ] [Arushi] Floating chat interface
- [ ] [Arushi] **Live Agent Reasoning Panel** wired to SSE
- [ ] [Arushi] Facility cards with confidence + transport buttons
- [ ] [Arushi] Dead Zone heatmap layer toggle
- [ ] [Arushi] Web Speech API voice input

### H 16-20 — All hands: integration
- [ ] End-to-end demo flow runs without errors
- [ ] Bug triage
- [ ] Multilingual voice input tested with at least one Hindi sample
- [ ] **Demo flow rehearsal #1** at H 19

### H 18-20 — Optional WhatsApp (Tero, only if integration is solid)
- [ ] [Tero] Twilio WhatsApp sandbox webhook
- [ ] [Tero] basic flow: WhatsApp message → agent → reply with top 3
- [ ] **Skip if integration is shaky.** Frontend hero is the priority.

### H 20-22 — Pitch deck (Tero)
- [ ] 5 slides: Problem → Architecture → Demo → Impact → Ask
- [ ] Backup demo recording captured

### H 22-24 — Final polish + rehearsal
- [ ] Pitch run-through ×2
- [ ] Backup demo recording stored locally + uploaded
- [ ] Devpost submission, GitHub polish, README

---

## 9. The Additions That Elevate It

Lifted from the source (Section 05). All four are flagged for impact-vs-time tradeoff.

| Addition | Time cost | Impact | Owner | Decision |
|---|---|---|---|---|
| **Multilingual Voice Input** | 15 min | Massive — India context demands it | Arushi | **Build always** |
| **Dead Zone Map Layer** | Automatic (pipeline computes it) | Maximum visual — problem + solution on one map | Danish + Arushi | **Build always** |
| **Confidence Scores** | One line per card | Technical-honesty signal for ML judges | Arushi | **Build always** |
| **WhatsApp Integration** | 2-3 hours | Differentiator — but eats integration budget | Tero | **Build if H 18 integration is solid; skip otherwise** |

---

## 10. The Pitch (under 3 minutes)

The PDF specifies a 4-beat structure. Reproduced verbatim:

**Beat 1 — Open with a real statistic.**
> *"India has 0.5 hospital beds per 1,000 people in rural areas vs the WHO recommendation of 2.5."*

**Beat 2 — Make the problem human.**
> *"Families don't just suffer from lack of healthcare — they suffer from lack of information about healthcare. People die traveling to hospitals that are full."*

**Beat 3 — Demo. Let the product speak.**
> Show the agent reasoning panel doing its thing. Don't narrate over it — let judges watch the AI think.

**Beat 4 — Close with scale.**
> *"AarogyaNet doesn't just build a map. It builds an intelligence network that gets smarter every time a family searches, every time a hospital updates, every time an agent learns a better route. This is what agentic AI looks like in the real world."*

---

## 11. Demo Theatre Discipline

**Rule:** the agent reasoning panel must be visibly streaming during every second of the live segment. Stale panel = wasted demo seconds.

For the live segment, this checklist must be satisfied:
- [ ] Hindi voice input works on first try (rehearsed)
- [ ] Triage Agent reasoning streams visibly within 1 second of input
- [ ] Map repaints when synthetic stream ticks during the demo (time the tick to land mid-pitch)
- [ ] At least one pin visibly shifts color (green → yellow or yellow → red) during pitch
- [ ] Confidence score visible on every card with `last_verified_at`
- [ ] Dead Zone toggle hits in the closing beat — full red overlay over rural Maharashtra
- [ ] Transport button click opens Ola/Uber app (not just visual)
- [ ] Ambulance number visible for HIGH urgency card

**Most important demo move:** the live stream tick happening mid-pitch. Time it. Practice it. *"And there it is — bed count just dropped at Hospital X."*

---

## 12. Demo Script (under 3 minutes)

**00:00-00:20 — Opener**
Slide: *"India: 0.5 beds per 1,000 in rural areas. WHO recommends 2.5. Families travel hours to hospitals that are full."* (PDF Beat 1)

**00:20-00:40 — The before-state**
Show the raw 10k spreadsheet on screen — mixed Hindi-English, missing fields, duplicate rows. *"This is what we start with."*

**00:40-01:00 — The pipeline**
Click "Run pipeline." Bronze → Silver → Gold animation. *"Data Cleaning Agent uses LLM function calls inside Delta Live Tables. Raw garbage in, clean intelligence out."*

**01:00-01:30 — The hero query (PDF Beat 3 — let the product speak)**
Open the app. Click the mic. Speak Hindi: «मेरे पिताजी को सांस नहीं आ रही, पैर सूज गए हैं». Transcript appears.
- **Reasoning panel streams** — Triage, then Availability, then Navigator.
- 3 facility cards render with ETA, confidence, transport buttons.
- *Time the synthetic stream tick to land here.* A pin on the map shifts color. *"And there — bed count just dropped at Hospital X."*

**01:30-01:50 — Dead Zone reveal**
Toggle Dead Zone layer. Rural Maharashtra lights up red. *"Same pipeline, second view. Where the gaps are, by district, automatically."*

**01:50-02:10 — Architecture beat**
One slide: 4-layer stack (Pipeline / Agents / Stream / Frontend). Logos: Databricks, OpenAI, Mapbox.

**02:10-02:30 — Closer (PDF Beat 4)**
*"AarogyaNet doesn't just build a map. It builds an intelligence network that gets smarter every time a family searches, every time a hospital updates, every time an agent learns a better route. This is what agentic AI looks like in the real world."*

---

## 13. Pre-Demo Checklist

Lifted verbatim from the source (Section 08). Every item must be green before the demo run-through.

- [ ] Raw messy data is ready and loaded — the "before" state is the opening hook
- [ ] Databricks pipeline runs end-to-end Bronze→Silver→Gold without errors
- [ ] All three agents callable via REST API (no console-only demos)
- [ ] Synthetic live update stream is running and visible on the map
- [ ] Agent reasoning panel is visible and updates in real time during demo
- [ ] At least one Hindi input tested and working
- [ ] Dead Zone heatmap layer toggleable on the map
- [ ] Facility cards show confidence scores and transport deeplinks
- [ ] Pitch is under 3 minutes + demo walkthrough
- [ ] Backup demo recording exists in case of live failure

---

## 14. Fallback Strategy

| Failure | Swap to | Setup before demo |
|---|---|---|
| Hindi voice fails on browser | Pre-typed Hindi text in chat | Have text ready in clipboard H 22 |
| Triage Agent slow/times out | Pre-cached response for the demo query | Cache H 22 |
| Live stream stops ticking | Manual tick button in dev panel | Wire button H 20 |
| Map tiles fail to load | Mapbox → fallback to OpenStreetMap tiles | Test fallback H 22 |
| OpenAI rate limit during demo | Pre-recorded video of full flow | Record H 22 |
| Pipeline live-run fails | Pre-recorded "before-after" timelapse | Record H 22 |
| WhatsApp Twilio sandbox dies | Skip that slide entirely | Have non-WhatsApp slide ready |
| REST API down | Frontend reads from local mock JSON | Mock JSON on disk H 22 |

**Rule (echoing source Section 07):** every "live" demo moment must have a pre-recorded version. No moment is "either live or nothing."

---

## 15. Risks & Open Questions

| Risk | Severity | Mitigation |
|---|---|---|
| Demo-first philosophy may underweight depth — judges who probe architecture deeply may find shallow spots (e.g., agent loop is linear ReAct, not true swarm) | High | Pitch frames the linear ReAct as a *deliberate* choice for demo-clarity ("we kept the Conductor simple — agent-to-agent communication for a 24h hack is over-engineering") — quote from source |
| Live agent reasoning panel only impresses if streams arrive fast (<200ms first token) | High | Use OpenAI streaming + SSE; pre-warm models; have cached response for the demo query as fallback |
| Synthetic live stream is honest but may strike judges as "fake" if pitched poorly | Medium | Honesty line lifted from source: *"In production this connects to IVR. In demo we simulate to show the architecture."* Lead with this, don't hide it |
| 10k Bronze→Silver→Gold pipeline running live during demo is risky | High | Pre-run the pipeline before demo; show "playback" of pipeline animation; only the live stream runs truly live |
| Free Edition limits on DLT, Model Serving, Vector Search | High | Tero H 0-2 spike validation; fall back to plain Spark + UC functions if DLT blocked |
| Three agents in linear chain — if one fails, demo dies | High | Each agent has cached fallback response; reasoning panel can replay cached tokens |
| Frontend load on Arushi is heaviest in this plan | High | Card layout + reasoning panel are the two musts; Dead Zone overlay is parallelizable; voice input is +15 min |
| WhatsApp integration eating integration budget | Medium | Hard rule: build only after H 18 integration green |
| Map of all India is heavy on Leaflet — perf risk | Medium | Focus on Maharashtra or UP bbox (source recommendation); render 100-500 pins, not 10k |
| "Build to the demo, not to completeness" requires saying no to scope creep | Medium | The One Rule (Section 16) is the team's north star; reread at every checkpoint |

---

## 16. The One Rule

Lifted verbatim from the source. This is the spec's north star.

> **DO NOT TRY TO BUILD EVERYTHING.**
>
> Judges are not using your product — they are evaluating your architecture, your demo, and your story. A polished demo of 70% of this plan beats a buggy demo of 100% every single time.
>
> Decide your exact demo flow in hours 0–2. Build to that flow. Don't deviate.

---

## 17. Out of Scope

- Real hospital APIs, IVR integrations, ABDM (replaced with synthetic stream — honest in pitch)
- True agent-to-agent multi-turn negotiation (linear ReAct only, by design)
- Atomic transactional booking (Navigator hands off to Ola/Uber/108 deeplinks; no commit)
- Outcome learning loop (no post-routing feedback)
- Patient-side authentication, PHI compliance work
- Multi-state ambulance number coverage beyond demo region
- Mobile-native app (web only; WhatsApp is the closest thing if time allows)
- Trust score with confidence intervals (replaced by simpler `confidence + last_verified_at` per card)

---

## 18. Success Criteria

**Demo-day pass:**
- Hindi voice input transcribes within 2s
- Reasoning panel streams visibly within 1s of input
- 3 facility cards render with confidence + last_verified_at + transport buttons
- Live stream ticks during pitch — at least one pin shifts color on screen
- Dead Zone overlay toggles cleanly, rural Maharashtra goes red
- Map URL deployed (Databricks App or backup Vercel)
- Pipeline animation plays cleanly (live or pre-recorded)
- Pitch lands all 4 beats in under 3 minutes
- Backup recording exists and has been viewed end-to-end

**Pitch quality:**
- Opens with the 0.5-vs-2.5 statistic (PDF Beat 1)
- Demo segment has zero narration over agent reasoning panel — let it speak
- Closer hits "intelligence network" line verbatim
- Architecture slide is one image (4-layer stack, logos)

**Rubric self-score target:**
- 35% Discovery & Verification — visible ReAct loop + per-card confidence + last_verified_at
- 30% IDP Innovation — DLT pipeline with LLM function calls (Bronze→Silver→Gold demo'd live)
- 25% Social Impact — Dead Zone heatmap layer + 0.5-vs-2.5 opener
- 10% UX/Transparency — agent reasoning panel streaming live

---

## 19. Comparison To Sibling Specs

This spec is one of three sibling proposals for the same hackathon (Challenge 03, same 4-person team, same 10k dataset). For side-by-side reading:

| | **This spec (AarogyaNet)** | `2026-04-25-healthcare-multiagent-design.md` (Tero) | `2026-04-25-healthcare-aarogya-trust-verification.md` (Aarogya AI) |
|---|---|---|---|
| **Killer** | Live agent reasoning panel + synthetic live stream + dead zones | Verify-All-4 + atomic booking + outcome loop + reputation | Extractor + Validator → contradictions → trust score with CI |
| **Posture** | Demo-first (build to flow, 70% > 100%) | Operational (book the bed) | Analytical (fix the data) |
| **Agents** | 3 (Triage, Availability, Navigator) in linear ReAct | 8+ in supervisor/sub-agent topology | 2 (Extractor, Validator) + 1 orchestrator |
| **Live data** | Synthetic ±2 beds / 5 min stream | IntakeAgent handshakes + outcome ping | None (batch pipeline) |
| **Voice** | Browser Web Speech API (Hindi, +15 min) | Tier-2 fallback (Fish Audio + OpenAI Realtime) | None |
| **NGO surface** | Dead Zone heatmap layer (toggle on hero map) | First-class desert dashboard (separate page) | First-class desert dashboard (separate page) |
| **Transport** | Ola/Uber/108 deeplinks (no commit) | Atomic 4-way Delta transaction + rollback | None |
| **Scope risk** | Medium — demo-first discipline contains it | High — 8 components, 4-way atomic txn | Low — small contract surface |
| **One Rule** | DO NOT BUILD EVERYTHING — quoted in spec | Implicit (fallback strategy is the discipline) | Implicit (small surface enforces it) |
