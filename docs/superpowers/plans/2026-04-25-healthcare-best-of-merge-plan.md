# Healthcare Multi-Agent — Best-Of Merge Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

> **Source spec:** `docs/superpowers/specs/2026-04-25-healthcare-best-of-merge.md` (1521 lines).
> Read it for the **why**. This document is the **how**.

**Goal:** Ship a demo-ready multi-agent healthcare intelligence system in 19 hours: Hindi voice symptom → 3 ranked hospitals with two-model trust verification → atomic 4-way Delta booking → live agent reasoning panel → outcome learning loop.

**Architecture:** Python FastAPI orchestration (BookingAgent supervisor + Triage / TrustScorer / Router / TransferCoord sub-agents) calling Databricks Foundation Model APIs (Llama 3.3 70B + Claude Opus 4.7) via `mlflow.deployments`. Data plane (DLT Bronze→Silver→Gold + atomic Delta booking + outcome feedback) lives in Databricks. React (Vite + Vercel) frontend with Web Speech API voice and EventSource SSE reasoning panel.

**Tech Stack:** Python 3.11+, FastAPI, `mlflow.deployments`, `databricks-sql-connector`, Pydantic, sklearn, FAISS (Mosaic AI Vector Search optional). React + Vite + Tailwind on Vercel, Leaflet, EventSource SSE. Databricks Trial for Work (Premium 14-day, $400 credits).

**Team:** Tero (orchestration + integration + demo), Mian (backend + data + agent logic), Arushi (frontend + submission). 3 strict folder lanes — never edit another owner's folder; cross-folder integration via `contracts/schemas.py` and `mocks/*_output.json`.

**The One Rule:** **DO NOT TRY TO BUILD EVERYTHING.** A polished demo of 70% beats a buggy demo of 100%. Build by layers; freeze at H 13 if Layer 2 not green.

---

## File Structure & Ownership Map

```
healthcare/
├── contracts/
│   ├── schemas.py                  # Tero — Pydantic from VF schema (MVP 0)
│   └── test_schemas.py             # Tero
├── mocks/
│   ├── trust_scorer_output.json    # Mian
│   ├── triage_output.json          # Mian
│   ├── router_output.json          # Tero
│   ├── transfer_output.json        # Tero
│   ├── reasoning_panel_event.json  # Tero
│   └── intake_handshake.json       # Mian
├── tero/
│   ├── supervisor/                 # FastAPI BookingAgent + SSE
│   ├── transfer/                   # Atomic 4-way booking
│   ├── router/                     # pandas/SQL ranking
│   ├── sim-stream/                 # Synthetic ±2 beds / 5 min
│   ├── outcome-loop/               # T+2h ping + retro-correction
│   ├── reputation/                 # Honest/total handshakes
│   └── integration/                # E2E pytest
├── mian/
│   ├── dlt-pipeline/               # Bronze→Silver→Gold
│   ├── triage/                     # Symptom→specialty
│   ├── trust-scorer/               # Two-model Extractor⇄Validator
│   ├── validator-rules/            # 3 contradiction rules
│   ├── intake-agent/               # Tier-1 mock FastAPI servers
│   ├── predictor/                  # Tier-2 sklearn forecaster
│   └── dead-zones/                 # PIN×specialty aggregation
├── arushi/
│   ├── app/                        # React + Vite + Vercel
│   ├── voice-input/                # Web Speech API
│   ├── reasoning-panel/            # EventSource SSE consumer
│   ├── click-to-source/            # MLflow trace modal
│   ├── ngo-dashboard/              # PIN-by-PIN dead zones
│   ├── dead-zone-overlay/          # Hero-map toggle
│   ├── animations/                 # Pulse / OutcomePing / StreamTick
│   └── submission/                 # README, demo video, Devpost
├── docs/
│   ├── demo-script.md              # Tero — locked at H 0-2
│   ├── edition-status.md           # Tero — Databricks Trial gates
│   └── pitch-deck/                 # Tero
└── data/
    └── VF_Hackathon_Dataset_India_Large.xlsx
```

---

## Layer Discipline (cuts before MVPs)

- **Layer 1 (База, H 0-7):** loop works end-to-end on stubs. **Not cuttable.**
- **Layer 2 (Улучшения базы, H 7-13):** real verification, click-to-source, atomic booking. **Hard checkpoint H 13.**
- **Layer 3 (Wow, H 13-16):** only if Layer 2 green. Each item has slide/animation replacement.
- **Layer 4 (Stretch, H 16+):** default = NOT BUILT. Only if Layer 3 fully shipped.

If you find yourself working on Layer 3 before Layer 2 is green: **stop**.

---

## MVP 0 — Setup (H 0-2)

**Goal:** All 3 owners start MVP 1 from green. Vercel URL live, Databricks edition gates verified, contracts published, demo flow locked.

### Task 0.1 — Tero: Edition validation & demo flow lock

**Files:**
- Create: `docs/edition-status.md`
- Create: `docs/demo-script.md`
- Create: `contracts/schemas.py`
- Create: `mocks/trust_scorer_output.json`, `mocks/router_output.json`, `mocks/reasoning_panel_event.json`, `mocks/transfer_output.json`
- Create: `tero/supervisor/__init__.py`, `tero/supervisor/main.py` (hello-world FastAPI)

- [ ] **Step 1: Provision Databricks Trial for Work workspace** in `us-east-1` or `us-west-2`. Add Mian + Arushi as workspace users.
- [ ] **Step 2: Run edition gates and post results in `docs/edition-status.md`:**
  ```python
  import mlflow.deployments
  client = mlflow.deployments.get_deploy_client("databricks")
  endpoints = [e["name"] for e in client.list_endpoints()]
  assert "databricks-meta-llama-3-3-70b-instruct" in endpoints
  assert "databricks-claude-opus-4-7" in endpoints
  ```
  Expected: both endpoints present. If missing → fall back per Section 12 fallback table in the spec.
- [ ] **Step 3: Verify outbound network** (secondary — only matters if FM API misses a model):
  ```python
  import requests
  requests.get("https://api.openai.com/v1/models", timeout=5)
  requests.get("https://api.anthropic.com/v1/models", timeout=5)
  ```
- [ ] **Step 4: Test Vector Search Trial allowance** — create a `storage-optimized` Delta-sync index with 1 endpoint. Confirm or note FAISS fallback.
- [ ] **Step 5: Scaffold DLT pipeline** — one Bronze→Silver dummy step. Confirm Lakeflow runs end-to-end on Trial.
- [ ] **Step 6: Pull `VF_Hackathon_Dataset_India_Large.xlsx`, extract pydantic schema → write `contracts/schemas.py`** with: `Hospital`, `TriageOutput`, `TrustScorerOutput` (with `Factor` sub-model carrying `extractor_confidence`, `validator_contradiction`, `ci`, `citation`), `RouterOutput`, `TransferCoordOutput`, `IntakeHandshake`, `OutcomeFeedback`, `ReasoningPanelEvent`.
- [ ] **Step 7: Write contract tests:**
  ```python
  # contracts/test_schemas.py
  from contracts.schemas import TrustScorerOutput
  def test_trust_scorer_shape_matches_spec_example():
      sample = json.load(open("mocks/trust_scorer_output.json"))
      TrustScorerOutput.model_validate(sample)  # raises if shape drifts
  ```
  Run: `pytest contracts/test_schemas.py -v`. Expected: PASS.
- [ ] **Step 8: Commit `mocks/*_output.json`** — sample JSON for every cross-folder contract. Use the example in spec section 3.3 for `trust_scorer_output.json`.
- [ ] **Step 9: Lock `docs/demo-script.md`** — second-by-second flow from spec section 11. Both full 2:30 and MVP-2-only 1:25 scripts. **Never deviate after this point.**
- [ ] **Step 10: Pick public-reachable FastAPI deploy** (Render / Fly.io / Railway / ngrok). Commit deploy config in `tero/supervisor/`. **No-go blocker for MVP 1 SSE** — Vercel React cannot SSE from `localhost`.
- [ ] **Step 11: FastAPI hello-world** in `tero/supervisor/main.py`:
  ```python
  from fastapi import FastAPI
  import mlflow.deployments
  app = FastAPI()
  client = mlflow.deployments.get_deploy_client("databricks")

  @app.get("/health")
  def health():
      return {"status": "ok", "fm_endpoints": len(client.list_endpoints())}
  ```
  Deploy. Expected: public URL returns 200 with non-zero endpoint count.
- [ ] **Step 12: Commit and push.** All three owners pull `main`, run MVP 0 acceptance.

### Task 0.2 — Mian: Stub gold + extraction prototype

**Files:**
- Create: `mian/dlt-pipeline/__init__.py`, `mian/dlt-pipeline/bronze.py`
- Create: `mian/trust-scorer/__init__.py`, `mian/trust-scorer/prototype.py`
- Stub Delta table: `main.healthcare.gold_hospitals` (50 hand-curated rows)

- [ ] **Step 1: Sniff `VF_Hackathon_Dataset_India_Large.xlsx`** — confirm column types with Tero before MVP 0 ends. Note any deviations from VF schema.
- [ ] **Step 2: Stub gold table — CRITICAL UNBLOCKER** (must land within H 0-1):
  ```sql
  CREATE TABLE main.healthcare.gold_hospitals (
    hospital_id STRING, name STRING, lat DOUBLE, lng DOUBLE,
    pin STRING, state STRING, specialties ARRAY<STRING>,
    procedures ARRAY<STRING>, equipment ARRAY<STRING>,
    capability ARRAY<STRING>, num_doctors INT, capacity INT,
    facility_type_id INT, description STRING, notes STRING,
    tier INT, trust DOUBLE, last_verified_at TIMESTAMP
  )
  ```
  Insert 50 hand-curated rows including: Hospital A (Tier 1, Patna, cardiology), Hospital B (Tier 2, near Patna), Hospital C (claims Advanced Surgery without anesthesiologist — for MVP 2 demotion demo), 47 generic Tier 2.
- [ ] **Step 3: Bronze stage scaffold** — `mian/dlt-pipeline/bronze.py` reads a CSV from S3/DBFS, writes to `main.healthcare.bronze_hospitals` with schema validation.
- [ ] **Step 4: Extraction prototype** — `mian/trust-scorer/prototype.py`:
  ```python
  import mlflow.deployments
  client = mlflow.deployments.get_deploy_client("databricks")
  resp = client.predict(
      endpoint="databricks-meta-llama-3-3-70b-instruct",
      inputs={
          "messages": [
              {"role": "system", "content": "Extract bed availability claim from facility note."},
              {"role": "user", "content": "Hospital A: 24/7 emergency, 200 beds..."},
          ],
          "temperature": 0.0,
      },
  )
  print(resp)
  ```
  Expected: structured JSON-ish response. Confirms FM API plumbing works end-to-end from external Python.

### Task 0.3 — Arushi: React + Vercel + EventSource hello-world

**Files:**
- Create: `arushi/app/` (Vite + React + TypeScript + Tailwind + Leaflet)
- Create: `arushi/reasoning-panel/EventSourceHelloWorld.tsx`
- Create: `arushi/app/vercel.json`

- [ ] **Step 1: Scaffold Vite app:**
  ```bash
  cd arushi/app && npm create vite@latest . -- --template react-ts
  npm install leaflet react-leaflet tailwindcss postcss autoprefixer
  npx tailwindcss init -p
  ```
- [ ] **Step 2: Connect Vercel** — `vercel link` then `vercel --prod`. Confirm one URL works (e.g., `https://aarogyanet.vercel.app`).
- [ ] **Step 3: EventSource hello-world** — `arushi/reasoning-panel/EventSourceHelloWorld.tsx`:
  ```tsx
  const es = new EventSource(import.meta.env.VITE_BOOKING_AGENT_URL + "/sse-test");
  es.onmessage = (e) => console.log("token:", e.data);
  ```
  Connects to Tero's hello-world SSE. Verify in browser console.
- [ ] **Step 4: Commit `vercel.json`** with environment variable `VITE_BOOKING_AGENT_URL` pointing at Tero's deployed FastAPI.

### MVP 0 acceptance

- [ ] All 3 owners have one commit on `main`.
- [ ] Vercel URL live and reachable.
- [ ] Tero's FastAPI deployed publicly; `/health` returns 200.
- [ ] `docs/edition-status.md` lists every Databricks gate with PASS/FAIL.
- [ ] `contracts/schemas.py` + `mocks/*_output.json` committed.
- [ ] `docs/demo-script.md` locked.
- [ ] Stub gold table queryable: `SELECT count(*) FROM main.healthcare.gold_hospitals` returns 50.

---

## MVP 1 — Working Loop (H 2-7)

**Demo state:** type or speak Hindi symptom → 3 hospital cards on map with mock trust scores → tap reserve → confirmation modal. Reasoning panel shows canned tokens. **No real verification yet — but the loop works end-to-end.**

### Task 1.1 — Tero: BookingAgent supervisor + Router + mock SSE + reserve stub

**Files:**
- Create: `tero/supervisor/booking_agent.py`, `tero/supervisor/sse_mock.py`, `tero/supervisor/reserve.py`
- Create: `tero/router/ranker.py`
- Create: `tero/supervisor/test_e2e.py`

- [ ] **Step 1: Write E2E smoke test FIRST:**
  ```python
  # tero/supervisor/test_e2e.py
  from fastapi.testclient import TestClient
  from tero.supervisor.main import app
  def test_recommend_returns_3_hospitals():
      client = TestClient(app)
      resp = client.post("/recommend", json={
          "symptoms": "बुखार और सीने में दर्द",
          "language": "hi",
          "lat": 25.59, "lng": 85.13,
      })
      assert resp.status_code == 200
      assert len(resp.json()["candidates"]) == 3
  ```
  Run: `pytest tero/supervisor/test_e2e.py -v`. Expected: FAIL with "endpoint not found".
- [ ] **Step 2: Implement `/recommend`** in `tero/supervisor/booking_agent.py`:
  - Accept `{symptoms, language, lat, lng}`.
  - Call Mian's TriageAgent (in-process import or HTTP — pick one and lock).
  - Call Mian's TrustScorer for top-N candidates (read Gold via `databricks-sql-connector`, pick nearest 50 by haversine).
  - Call `tero.router.ranker.rank()` → top 3.
  - Return `{candidates: [...], trace_id: ...}`.
- [ ] **Step 3: Implement Router** — `tero/router/ranker.py`:
  ```python
  def rank(candidates: list[dict], top_k: int = 3) -> list[dict]:
      # Score = trust * 0.5 + (1 / (1 + travel_min/30)) * 0.3 + specialty_match * 0.2
      ...
  ```
  Reads from `main.healthcare.gold_hospitals` via `databricks-sql-connector`.
- [ ] **Step 4: Mock SSE** — `tero/supervisor/sse_mock.py` exposes `/sse?session_id=...` that streams a canned sequence: `🩺 triage → 🔍 extractor → 🛡 validator → 🗺 router` over ~3 seconds. Arushi's panel consumes this in MVP 1.
- [ ] **Step 5: Reserve stub** — `tero/supervisor/reserve.py`: `POST /reserve` returns `{confirmed: true, eta_min: 23, atomic_txn_id: "stub_mvp1"}`. Real Delta INSERT lands in MVP 2.
- [ ] **Step 6: Run E2E test, verify pass:** `pytest tero/supervisor/test_e2e.py -v`. Expected: PASS.
- [ ] **Step 7: Commit:**
  ```bash
  git add tero/supervisor/ tero/router/
  git commit -m "tero: booking agent supervisor + router + mock sse + reserve stub"
  ```

### Task 1.2 — Mian: DLT real (100 hospitals) + TriageAgent + TrustScorer v1 single-model

**Files:**
- Create: `mian/dlt-pipeline/silver.py`, `mian/dlt-pipeline/gold.py`
- Create: `mian/triage/triage.py`, `mian/triage/symptom_corpus.json`
- Create: `mian/trust-scorer/v1_single_model.py`

- [ ] **Step 1: Expand DLT to 100 hospitals** — Bronze→Silver→Gold:
  - Silver (`mian/dlt-pipeline/silver.py`): geocode missing lat/lng (geopy), dedupe by fuzzy name + 500m radius, normalize specialties to canonical taxonomy, language-detect notes.
  - Gold (`mian/dlt-pipeline/gold.py`): aggregate to one row per hospital with all fields ready for trust scoring. Replace stub gold table on commit.
- [ ] **Step 2: Symptom corpus** — `mian/triage/symptom_corpus.json` with ~50 symptom→specialty mappings (English + Hindi). Example: `"सीने में दर्द": ["cardiology", "pulmonology"]`.
- [ ] **Step 3: TriageAgent test FIRST:**
  ```python
  # mian/triage/test_triage.py
  from mian.triage.triage import triage
  def test_hindi_chest_pain_routes_to_cardiology():
      out = triage(symptoms_text="बुखार और सीने में दर्द", language="hi")
      assert out["specialty"] == "cardiology"
      assert out["urgency"] >= 2
      assert out["confidence"] > 0.5
  ```
  Run: FAIL with "function not defined".
- [ ] **Step 4: Implement TriageAgent** — `mian/triage/triage.py`:
  ```python
  import mlflow.deployments
  client = mlflow.deployments.get_deploy_client("databricks")
  def triage(symptoms_text: str, language: str) -> dict:
      resp = client.predict(
          endpoint="databricks-meta-llama-3-3-70b-instruct",
          inputs={
              "messages": [
                  {"role": "system", "content": TRIAGE_PROMPT_WITH_CORPUS},
                  {"role": "user", "content": symptoms_text},
              ],
              "temperature": 0.0,
          },
      )
      return parse_to_TriageOutput(resp)
  ```
- [ ] **Step 5: Run triage test, verify pass.**
- [ ] **Step 6: TrustScorer v1 single-model** — `mian/trust-scorer/v1_single_model.py`:
  - Single Llama 3.3 70B call per facility, asks for 4 factor scalars (bed/oxygen/drug/specialist).
  - Returns `TrustScorerOutput` with scalar trust + per-factor scalars (no CI yet, no Validator yet).
  - Reads facility row from Gold via `databricks-sql-connector`.
- [ ] **Step 7: Commit `mocks/trust_scorer_output.json`** matching v1 shape so Tero + Arushi can render against it.
- [ ] **Step 8: Commit:**
  ```bash
  git add mian/dlt-pipeline/ mian/triage/ mian/trust-scorer/v1_single_model.py mocks/trust_scorer_output.json
  git commit -m "mian: dlt 100 hospitals + triage agent + trust scorer v1 single-model"
  ```

### Task 1.3 — Arushi: Patient flow UI + voice + reasoning panel skeleton

**Files:**
- Create: `arushi/app/src/pages/PatientFlow.tsx`
- Create: `arushi/app/src/components/HospitalCard.tsx`, `arushi/app/src/components/IndiaMap.tsx`
- Create: `arushi/voice-input/useWebSpeech.ts`
- Create: `arushi/reasoning-panel/ReasoningPanel.tsx`

- [ ] **Step 1: Patient flow page** — chat input on top, India map (Leaflet, focus on Patna 25.59°N 85.13°E), 3 hospital cards on right, reasoning panel collapsible side. Tailwind layout.
- [ ] **Step 2: `IndiaMap.tsx`** — Leaflet map with markers for the 3 returned hospitals, color-coded by trust (green ≥0.8, yellow 0.5-0.8, red <0.5).
- [ ] **Step 3: `HospitalCard.tsx`** — name, distance, 4-factor trust badges (bed/oxygen/drug/specialist), Reserve button. Read from `/recommend` response shape.
- [ ] **Step 4: `useWebSpeech.ts`** — Web Speech API hook:
  ```typescript
  const recognition = new (window.webkitSpeechRecognition || window.SpeechRecognition)();
  recognition.lang = 'hi-IN';
  recognition.onresult = (e) => onTranscript(e.results[0][0].transcript);
  ```
- [ ] **Step 5: `ReasoningPanel.tsx`** — EventSource consumer at `${VITE_BOOKING_AGENT_URL}/sse?session_id=...`. Render tokens as they stream, group by agent (`triage` 🩺, `extractor` 🔍, `validator` 🛡, `router` 🗺).
- [ ] **Step 6: Reserve button** — POST to `/reserve`, show confirmation modal with `{eta_min, atomic_txn_id}`.
- [ ] **Step 7: Manual smoke test on Vercel deploy** — speak Hindi, see 3 hospitals, panel streams, reserve confirms.
- [ ] **Step 8: Commit:**
  ```bash
  git add arushi/app/ arushi/voice-input/ arushi/reasoning-panel/
  git commit -m "arushi: patient flow + web speech voice + reasoning panel skeleton"
  ```

### MVP 1 acceptance @ H 7

- [ ] User on Vercel URL: speak Hindi symptom → 3 hospital cards within 5 seconds.
- [ ] Reasoning panel shows canned tokens streaming during call.
- [ ] Reserve button shows confirmation modal.
- [ ] No manual intervention for full demo run.
- [ ] `pytest tero/supervisor/test_e2e.py mian/triage/test_triage.py contracts/test_schemas.py` all green.
- [ ] **15-min standup:** all 3 owners show their folder running locally. If MVP 1 not green → freeze, debug, do not start MVP 2.

**Stop here if catastrophic.** You still have a healthcare-finder demo judges can use.

---

## MVP 2 — Atomic + Two-Model + Reasoning + Click-to-Source (H 7-13)

**This is the rubric-pass MVP.** Combines operational killer (atomic booking) + rubric anchors (two-model + click-to-source) + demo killer (real reasoning panel).

### Task 2.1 — Tero: Atomic 4-way booking + real SSE + failure-and-retry

**Files:**
- Create: `tero/transfer/atomic.py`, `tero/transfer/mock_endpoints.py`
- Modify: `tero/supervisor/sse_mock.py` → `tero/supervisor/sse_real.py`
- Modify: `tero/supervisor/reserve.py` (call `book_atomic`)
- Create: `tero/transfer/test_atomic.py`

- [ ] **Step 1: Wait for Mian's schema migration** — `main.healthcare.atomic_bookings` table with struct columns must land first (Task 2.2 step 1).
- [ ] **Step 2: Mock side-effect endpoints** — `tero/transfer/mock_endpoints.py`:
  - Port 9101: `/bed_reserve` returns `{reservation_id, ward, eta_min}` or `409 Conflict`.
  - Port 9102: `/ambulance_dispatch` returns `{dispatch_id, eta_min}` or `503`.
  - Port 9103: `/doctor_slot_hold` (Tier 2) returns `{slot_id, doctor_name}` or `409`.
  - Port 9104: `/drug_reserve` returns `{lock_id, sku}` or `409 stockout`.
  - Hospital A's drug endpoint **seeded to fail with 409 stockout** for the demo failure-and-retry beat.
- [ ] **Step 3: Atomic booking test FIRST:**
  ```python
  # tero/transfer/test_atomic.py
  from tero.transfer.atomic import book_atomic
  def test_all_4_pass_writes_single_row():
      result = book_atomic(hospital_id="hospital_b", factors_required={...})
      assert result["atomic_txn_id"] is not None
      # Verify single row in atomic_bookings
      ...
  def test_drug_409_returns_no_commit():
      result = book_atomic(hospital_id="hospital_a", factors_required={...})
      assert result["atomic_txn_id"] is None
      assert result["rollback_reason"] == "drug_409_stockout"
  ```
  Run: FAIL.
- [ ] **Step 4: Implement `book_atomic`** — `tero/transfer/atomic.py`:
  ```python
  async def book_atomic(hospital_id: str, factors_required: dict) -> dict:
      # 1. Parallel async HTTP probes (asyncio.gather)
      probes = await asyncio.gather(
          probe_bed(hospital_id), probe_ambulance(hospital_id),
          probe_doctor(hospital_id), probe_drug(hospital_id),
      )
      # 2. If ANY fails → return {atomic_txn_id: None, rollback_reason: ...}
      if any(not p["ok"] for p in probes):
          return {"atomic_txn_id": None, "rollback_reason": _which_failed(probes)}
      # 3. Single-row INSERT with struct columns
      with sql.connect(...) as conn:
          conn.cursor().execute("""
              INSERT INTO main.healthcare.atomic_bookings (
                txn_id, hospital_id, patient_session_id, ts,
                bed_reservation, ambulance_dispatch, doctor_slot, drug_reservation
              ) VALUES (?, ?, ?, current_timestamp(),
                struct(?, ?, ?), struct(?, ?), struct(?, ?), struct(?, ?))
          """, [...])
      return {"atomic_txn_id": txn_id, "factors_locked": ["bed", "oxygen", "drug", "specialist"]}
  ```
  **No multi-statement Delta tx** — single-row write IS the atomic unit at the SQL connector layer. Pre-validation BEFORE INSERT avoids rollback.
- [ ] **Step 5: Run atomic tests, verify pass.**
- [ ] **Step 6: Real SSE** — `tero/supervisor/sse_real.py`:
  - Replace mock canned tokens with real streamed tokens from each agent.
  - Emit distinct event types: `triage`, `extractor`, `validator`, `router`, `transfer` (so frontend can color-code).
  - Server-side relay of FM API streams via `mlflow.deployments` (predict with stream=True or polling) → SSE to client.
- [ ] **Step 7: Upgrade `/reserve`** to call `book_atomic` and return `{atomic_txn_id, factors_locked, rollback_reason}`.
- [ ] **Step 8: Demo failure-and-retry script test** — manual: Reserve A → drug fails → 4 tiles flash red → BookingAgent auto-suggests B → 4 probes pass → 4 tiles flip green.
- [ ] **Step 9: Commit:**
  ```bash
  git add tero/transfer/ tero/supervisor/sse_real.py tero/supervisor/reserve.py
  git commit -m "tero: atomic 4-way booking with single-row delta + real sse + failure-retry"
  ```

### Task 2.2 — Mian: Two-model TrustScorer + per-field CI + click-to-source + 3 rules

**Files:**
- Create: `mian/trust-scorer/v2_two_model.py`
- Create: `mian/trust-scorer/precompute.py`
- Create: `mian/trust-scorer/mlflow_trace.py`
- Create: `mian/dlt-pipeline/silver_sentences.py`
- Create: `mian/validator-rules/rules.py`
- DDL: `main.healthcare.atomic_bookings`, `main.healthcare.silver_facility_sentences`

- [ ] **Step 1: Schema migration — `main.healthcare.atomic_bookings`** (BLOCKS Tero's atomic.py — H 7 deliverable):
  ```sql
  CREATE TABLE main.healthcare.atomic_bookings (
    txn_id STRING, hospital_id STRING, patient_session_id STRING,
    ts TIMESTAMP,
    bed_reservation STRUCT<reservation_id: STRING, ward: STRING, eta_min: INT>,
    ambulance_dispatch STRUCT<dispatch_id: STRING, eta_min: INT>,
    doctor_slot STRUCT<slot_id: STRING, doctor_name: STRING>,
    drug_reservation STRUCT<lock_id: STRING, sku: STRING>
  ) USING DELTA
  ```
  **Tero is blocked on this. Land it first thing in MVP 2.**
- [ ] **Step 2: Sentence pre-indexing in Silver** — `mian/dlt-pipeline/silver_sentences.py`:
  ```python
  import nltk
  nltk.download("punkt")
  for hospital_id, note in facility_notes.items():
      paragraphs = note.split("\n\n")
      for p_idx, para in enumerate(paragraphs):
          for s_idx, sent in enumerate(nltk.sent_tokenize(para)):
              yield {
                  "sentence_id": f"{hospital_id}_p{p_idx}_s{s_idx}",
                  "hospital_id": hospital_id,
                  "paragraph_idx": p_idx,
                  "sentence_idx": s_idx,
                  "text": sent,
              }
  ```
  Write to `main.healthcare.silver_facility_sentences`. **Blocks click-to-source.**
- [ ] **Step 3: Two-model TrustScorer** — `mian/trust-scorer/v2_two_model.py`:
  ```python
  client = mlflow.deployments.get_deploy_client("databricks")

  def score(hospital_id: str) -> TrustScorerOutput:
      # Read disjoint slices
      notes = read_notes_with_sentence_ids(hospital_id)        # → Extractor
      rosters = read_rosters_with_row_ids(hospital_id)         # → Validator
      equipment = read_equipment_with_row_ids(hospital_id)     # → Validator

      # Extractor on notes
      extractor_resp = client.predict(
          endpoint="databricks-meta-llama-3-3-70b-instruct",
          inputs={"messages": [
              {"role": "system", "content": EXTRACTOR_PROMPT},  # asks for citation_id
              {"role": "user", "content": notes},
          ], "temperature": 0.0},
      )

      # Validator on rosters/equipment — different family, disjoint slice
      validator_resp = client.predict(
          endpoint="databricks-claude-opus-4-7",
          inputs={"messages": [
              {"role": "system", "content": VALIDATOR_PROMPT},  # asks for counter_row_id
              {"role": "user", "content": rosters + equipment},
          ], "temperature": 0.0},
      )

      # Compose: extractor_confidence × (1 - validator_contradiction) × evidence_completeness
      # Per-factor mean ± 95% CI from bootstrap or hardcoded for demo
      return compose_trust_scorer_output(extractor_resp, validator_resp)
  ```
- [ ] **Step 4: Validator rule pack** — `mian/validator-rules/rules.py`:
  ```python
  def no_anesthesiologist(roster: list[dict]) -> dict:
      has_anesth = any("anesth" in r["title"].lower() for r in roster)
      if not has_anesth and any_advanced_surgery_claim(roster):
          return {"matched": True, "evidence_pointer": "roster_row_44", "confidence": 0.92}
      return {"matched": False}

  def no_ventilators(equipment: list[dict]) -> dict: ...
  def no_night_staff(roster: list[dict]) -> dict: ...
  ```
- [ ] **Step 5: MLflow trace endpoint** — `mian/trust-scorer/mlflow_trace.py`:
  ```python
  @app.get("/trace/{trust_score_id}")
  def get_trace(trust_score_id: str):
      run = mlflow.get_run(trust_score_id)
      citation_id = run.data.tags["citation_id"]
      sentence_text = lookup(silver_facility_sentences, citation_id)
      counter_row_id = run.data.tags["counter_row_id"]
      counter_row_text = lookup(silver_rosters, counter_row_id)
      return {
          "citation_id": citation_id, "sentence_text": sentence_text,
          "counter_row_id": counter_row_id, "counter_row_text": counter_row_text,
      }
  ```
- [ ] **Step 6: Pre-compute Gold on 100-200 hospitals** — `mian/trust-scorer/precompute.py`:
  - Run `score()` over 100-200 rows offline, write results back to Gold. Demo reads frozen Gold (latency-safe).
  - Hand-curate Hospital C: claims "Advanced Surgery 24/7" + roster has no anesthesiologist → contradiction conf 0.92, demoted.
- [ ] **Step 7: Test contradiction detection:**
  ```python
  def test_hospital_c_demoted():
      result = score(hospital_id="hospital_c")
      assert result.factors["specialist"].validator_contradiction >= 0.9
      assert result.trust < 0.3
  ```
- [ ] **Step 8: Commit and push.**

### Task 2.3 — Arushi: 4-tile flip + click-to-source modal + real SSE + DEMOTED badge + CI display

**Files:**
- Create: `arushi/app/src/components/AtomicBookingTiles.tsx`
- Create: `arushi/click-to-source/SourceModal.tsx`
- Modify: `arushi/reasoning-panel/ReasoningPanel.tsx` (real SSE, color-coded)
- Modify: `arushi/app/src/components/HospitalCard.tsx` (DEMOTED badge, CI display)

- [ ] **Step 1: `AtomicBookingTiles.tsx`** — 4 tiles (bed/oxygen/drug/specialist) with flip animation:
  - Initial: grey.
  - On `/reserve` response with `atomic_txn_id` → all 4 flip green simultaneously.
  - On `rollback_reason` → all 4 flash red, reset to grey, show toast "drug stockout — auto-suggesting Hospital B".
- [ ] **Step 2: `SourceModal.tsx`** — opens on Trust factor click:
  - Calls `GET /trace/{trust_score_id}`.
  - Renders the original facility note with `sentence_text` highlighted in yellow.
  - Renders the staff roster with `counter_row_text` highlighted in red.
  - **The rubric click moment.**
- [ ] **Step 3: Real SSE** — `ReasoningPanel.tsx`:
  - Switch from mock to real EventSource at `/sse_real`.
  - Color-code by event type: triage blue, extractor purple, validator red, router green, transfer orange.
  - 5 distinct token streams visible.
- [ ] **Step 4: HospitalCard.tsx upgrades:**
  - Per-factor display: `0.94 ± 0.03` (mean ± CI).
  - Red "DEMOTED" badge when `validator_contradiction > 0.5`, with hover tooltip showing the rule that fired.
  - Each factor click-able → opens `SourceModal`.
- [ ] **Step 5: Manual demo run** on Vercel: voice → 3 cards (C demoted) → click factor on C → modal shows highlighted sentence + roster row → Reserve A → 4 tiles red flash → auto-suggest B → 4 green.
- [ ] **Step 6: Commit and push.**

### MVP 2 acceptance @ H 13 — HARD CHECKPOINT

- [ ] All MVP 1 criteria still pass.
- [ ] Hospital C visibly demoted with red "no anesthesiologist" badge.
- [ ] Click any Trust factor → modal opens with source sentence highlighted + counter-evidence row.
- [ ] Reserve A → 4 tiles attempt → drug fails → all flash red → rollback → auto-suggest B → 4 tiles green.
- [ ] Reasoning Panel streams 5 distinct color-coded agent token types.
- [ ] Each factor shows `mean ± CI` instead of single number.
- [ ] `pytest tero/transfer/test_atomic.py mian/trust-scorer/test_*` all green.

⚠ **HARD CHECKPOINT @ H 13** — *the* checkpoint of the hackathon.

If MVP 2 NOT green → **stop everything**. Use H 13-19 to polish MVP 1+2 only, pre-record fallbacks, rehearse pitch. MVP 3 never started. **This is The One Rule firing.**

If MVP 2 minimum viable cut is needed at H 11: drop two-model to single-model with hardcoded validator contradiction for Hospital C; drop 2 of 3 rules; click-to-source on ONE factor; real SSE on ONE agent (extractor).

---

## MVP 3 — Tier-1/2 + Stream + Outcome + NGO + Polish (H 13-19)

**Operational depth + social impact + final polish.**

### Task 3.1 — Tero: sim-stream + outcome loop + reputation + tier routing + integration + 3 rehearsals

**Files:**
- Create: `tero/sim-stream/stream.py`
- Create: `tero/outcome-loop/loop.py`
- Create: `tero/reputation/aggregate.py`
- Create: `tero/supervisor/tier_routing.py`
- Create: `tero/integration/test_full_flow.py`
- Create: `docs/pitch-deck/counterfactual-opener.png`

- [ ] **Step 1: Synthetic Live Stream** — `tero/sim-stream/stream.py`:
  - Cron or scheduled job. Picks 30 random Tier-2 rows. Applies `bed_count += randint(-2, +2)`, occasional `icu_full=True`. Appends to `main.healthcare.bed_updates` Delta table. WebSocket broadcasts to React for live pin re-color.
  - **Time the demo tick to land mid-pitch.**
- [ ] **Step 2: Outcome loop** — `tero/outcome-loop/loop.py`:
  - Simulates T+2h ping (no real Twilio). Appends to `main.healthcare.outcome_feedback`. Retro-corrects Trust factor via SQL UPDATE on Gold.
  - Animation contract for Arushi's playback.
- [ ] **Step 3: Reputation** — `tero/reputation/aggregate.py`:
  ```sql
  SELECT hospital_id,
         COUNT(*) FILTER (WHERE patient_confirmed = true) * 1.0 / COUNT(*) AS reputation
  FROM main.healthcare.outcome_feedback
  GROUP BY hospital_id
  ```
  Pre-rendered React data passed to Arushi for animated card stack.
- [ ] **Step 4: Tier routing** — `tero/supervisor/tier_routing.py`:
  - Tier-1 (HAS-AGENT) → call IntakeAgent endpoint (Mian's mock servers).
  - Tier-2 (NO-AGENT) → BedPredictor + Synthetic Stream + voice fallback (Mode B Layer 4 only).
- [ ] **Step 5: Integration E2E test** — `tero/integration/test_full_flow.py`:
  - Walks: voice transcript → 3 cards → Validator demotion → Reserve → atomic commit → outcome ping → reputation tick → NGO dashboard query.
  - Run before each rehearsal.
- [ ] **Step 6: Counterfactual opener slide** — `docs/pitch-deck/counterfactual-opener.png` with stat: *"38 lives changed in 90 days, simulated from research/01"*.
- [ ] **Step 7: 3 demo rehearsals at H 17, H 18, H 19** with the team. Fix timing/audio.

### Task 3.2 — Mian: IntakeAgent mocks + Dead Zone aggregation + Predictor + Tier-1 onboarding

**Files:**
- Create: `mian/intake-agent/server.py` (template)
- Run instances on ports 9201, 9202, 9203
- Create: `mian/dead-zones/aggregate.py`
- Create: `mian/predictor/forecaster.py`

- [ ] **Step 1: IntakeAgent FastAPI mock template** — `mian/intake-agent/server.py`:
  - Endpoints: `bed?`, `oxygen?`, `drug?`, `specialist?` returning yes/no with mock signature header.
  - Configurable hospital_id per port.
- [ ] **Step 2: Run 3 instances:**
  - Hospital A on 9201 → all 4-yes (will pulse green).
  - Hospital B on 9202 → 3-yes 1-no.
  - Hospital D on 9203 → 1-no (Validator demotion supplement).
- [ ] **Step 3: Dead Zone aggregation** — `mian/dead-zones/aggregate.py`:
  ```python
  @app.get("/dead-zones")
  def dead_zones(specialty: str | None = None, min_trust: float = 0.6):
      return query_gold_grouped_by_pin_specialty(specialty, min_trust)
  ```
  Returns `{pin: {specialty: {count, min_trust, nearest_km}}}`.
- [ ] **Step 4: BedPredictor** — `mian/predictor/forecaster.py` — sklearn forecaster, joblib serialized, history-only. Loaded by Tero's BookingAgent for Tier-2.
- [ ] **Step 5: Hand-curate** Hospital A and B as Tier-1 partners in stub gold table.
- [ ] **Step 6: (if time) expand Validator rule pack to 6 rules.**

### Task 3.3 — Arushi: NGO Dashboard + Dead Zone overlay + animations + submission

**Files:**
- Create: `arushi/ngo-dashboard/NGODashboard.tsx`
- Create: `arushi/dead-zone-overlay/DeadZoneToggle.tsx`
- Create: `arushi/animations/GreenPulse.tsx`, `arushi/animations/OutcomePing.tsx`, `arushi/animations/StreamTick.tsx`
- Create: `arushi/submission/README.md`, `arushi/submission/demo-video.mp4`

- [ ] **Step 1: NGO Dashboard tab** — `arushi/ngo-dashboard/NGODashboard.tsx`:
  - India PIN map (Leaflet GeoJSON).
  - Filter dropdown: specialty + min trust threshold.
  - Click PIN → "0 dialysis within 80km, population 4.2M" detail card.
  - Calls `/dead-zones` REST endpoint.
- [ ] **Step 2: Dead Zone overlay** — `arushi/dead-zone-overlay/DeadZoneToggle.tsx`:
  - Toggle button on hero map. Overlays same Dead Zone GeoJSON as red heatmap. One-tap on/off.
- [ ] **Step 3: Animations:**
  - `GreenPulse.tsx` — Tier-1 hospital cards get green "Verified Live" pulse on IntakeAgent 4-yes.
  - `OutcomePing.tsx` — replay: clock advances → SMS bubble → trust drops → reputation card-stack ticks one notch.
  - `StreamTick.tsx` — pin color shift on WebSocket message from Tero's stream.
- [ ] **Step 4: Pre-recorded fallback videos** for every "live" moment: voice / reasoning / atomic / stream tick / NGO toggle. Stored in `arushi/submission/fallbacks/`.
- [ ] **Step 5: Submission package** — `arushi/submission/`:
  - `README.md` — architecture diagram screenshot, run instructions, demo video link.
  - `demo-video.mp4` — rehearsal recording.
  - Devpost writeup draft.
  - GitHub polish.

### MVP 3 acceptance @ H 19

- [ ] All MVP 2 criteria still pass.
- [ ] Hospital A shows green "Verified Live" pulse (Tier-1 IntakeAgent handshake).
- [ ] Synthetic Stream tick lands during pitch — at least one pin visibly shifts color.
- [ ] Outcome Loop animation plays on demand.
- [ ] NGO Dashboard tab loads PIN map; dialysis layer toggles to red over Bihar.
- [ ] Dead Zone overlay toggles on hero map (one-tap red).
- [ ] Submission package complete in GitHub.
- [ ] Backup demo recording exists for every live moment.
- [ ] 3 full rehearsals complete without team intervention.

---

## Layer 3 (H 13-16, only if MVP 2 green)

Each item has slide/animation replacement — pitch survives without it.

| Component | Owner | If not built |
|---|---|---|
| Agent Reputation Score live aggregation | Tero | Pre-rendered card-stack animation |
| Doctor Transfer Copilot tab | Mian + Arushi | Screenshot in pitch deck |
| FHIR snippet generation | Mian | Faked JSON with "FHIR-compatible" caption |
| Genie Code multi-step query | Tero | Pre-recorded screen capture |
| MLflow Registry + lineage view | Mian | Static screenshot |
| BedPredictor MLflow Registry serving | Mian | Local serialized sklearn |
| Validator full 10+ rules | Mian | 3 rules from Layer 2 |
| Vector Search citation retrieval | Mian | Local FAISS from Gold |
| IntakeAgent UC-signed identity | Mian | Mock signature string |
| Two-model precompute on full 10k | Mian | 100-200 from Layer 2 |

## Layer 4 (H 16+, default NOT BUILT)

- Voice MCP Mode B (Fish + OpenAI Realtime + outbound calls) — 6h cost.
- Bridge Doctor Mode (D2D shared screen).
- Ambulance moving animation.
- Real Twilio Media Streams.
- Real outcome scheduled job + Twilio/SMS ping.
- Mosaic AI Agent Framework — thin-wrapper registration of existing FastAPI BookingAgent (~1-2h cost; pitch line: "we use Agent Bricks").
- Mosaic AI Knowledge Assistant for Triage corpus.

---

## Verification & Demo Theatre Discipline

**Every "live" demo moment must have a pre-recorded fallback by H 18.**

Hierarchy of "if only one thing works" priorities:
1. Reasoning Panel streaming via FastAPI SSE
2. Atomic Booking 4-tile flip on Delta
3. Click-to-source MLflow trace on at least one factor
4. Validator demotion visible on one hospital
5. Synthetic Stream tick during pitch

If those 5 work plus MVP 1 base, the demo passes.

### Per-component fallbacks (table from spec section 12)

| Failure | Swap to | Setup before demo |
|---|---|---|
| Reasoning Panel streams stop mid-demo | Cached token playback | H 18 record cached run |
| Synthetic Stream stops ticking | Manual "force tick" button | H 16 wire button |
| Hindi voice fails on browser | Pre-typed Hindi in clipboard | H 18 |
| FM API endpoint missing | Closest-available endpoint or external SDK | H 0 validation gate |
| Vercel deploy down | `localhost:5173`; Databricks App URL backup | Keep `npm run dev` warm H 16-18 |
| BookingAgent crashes mid-demo | Mock SupervisorResponse JSON file → frontend reads local | File on disk H 16-18 |
| Atomic Booking transaction fails on stage | Backup video of successful run | Record H 16-18 |
| TrustScorer two-model latency too high | Pre-compute Gold offline; demo reads frozen Gold | Pre-compute H 13 |
| Dead Zone overlay slow on full geo data | Pre-aggregate static GeoJSON | H 15 |

---

## Cross-MVP Rules (apply throughout)

- **Never edit another owner's folder.** Open a PR or commit a contract example in `contracts/` or `mocks/`.
- **All "live" demo moments need pre-recorded fallback by H 18.**
- **Demo flow document never deviates from the H 0-2 lock.**
- **Daily integration green** — every MVP boundary requires `pytest tero/integration/` green on `main` before next MVP starts.
- **15-min standup at every MVP boundary** (H 7, H 13, H 19).
- **5-min sync at H 11** (informal MVP 2 health check) — if 3+ items not working, switch to MVP 2 minimum viable cut now.

---

## Success Criteria (rubric self-score target)

- 35% Discovery & Verification — two-model TrustScorer + Validator + Outcome Loop + Reputation
- 30% IDP Innovation — 4-factor extraction with two-model verification + click-to-source + LLM-in-DLT cleaning
- 25% Social Impact — NGO Desert Dashboard + Dead Zone overlay + Counterfactual Replay
- 10% UX/Transparency — Reasoning Panel streaming + click-to-source on every Trust factor
