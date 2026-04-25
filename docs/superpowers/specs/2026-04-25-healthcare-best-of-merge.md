# Healthcare Multi-Agent — Best-Of Merge Spec

> **Approach:** Best-of merge across the three sibling specs (Tero / Friend 1 / Friend 2). Operational depth from Tero, two-model verification from Friend 1, live reasoning theatre from Friend 2. Conflicts deliberately resolved, every component tagged with provenance.
> **Source specs:**
>   - `2026-04-25-healthcare-multiagent-design.md` (Tero — operational, two-tier coverage, outcome loop)
>   - `2026-04-25-healthcare-aarogya-trust-verification.md` (Friend 1 — two-agent verification, per-field trust, click-to-source)
>   - `2026-04-25-healthcare-aarogyanet-react-swarm.md` (Friend 2 — reasoning panel, synthetic stream, scope discipline)
> **Stack split:** Databricks for **data layer only** (DLT pipeline + Delta tables + atomic booking commit + optional Vector Search) **and model serving** (Llama 3.3 70B + Claude Opus 4.7 via Foundation Model APIs, called from external Python via `mlflow.deployments`). Python + FastAPI for agent logic (orchestration runs *outside* Databricks). React (Vercel) for frontend. **External OpenAI/Anthropic SDKs are last-resort fallback only** (used if a specific FM API endpoint is missing on Trial). **See "Stack Boundary" section below.**
> **Edition:** **Databricks Trial for Work (14-day Premium, $400 credits)** primary. Free Edition is the catastrophic-fallback. Trial restores Mosaic AI Vector Search (1 endpoint cap), Lakehouse Monitoring, Genie Code, multi-App. Trial caveats survive: outbound network is still restricted to a limited domain whitelist; trial expires day 14 with 60-day grace. See `research/09-databricks-editions.md` for the full audit.
> **Challenge:** Serving A Nation — Building Agentic Healthcare Maps for 1.4 Billion Lives (Challenge 03, see `docs/challenge-brief.md`)
> **Last updated:** 2026-04-25

**Provenance tag legend** (applied per component):
- **[T]** — taken from Tero's spec
- **[F1]** — taken from Friend 1's spec (Aarogya AI)
- **[F2]** — taken from Friend 2's spec (AarogyaNet)
- **[H]** — hybrid (combines two or more sources)

---

## ⚠ The One Rule (carried from Friend 2 — applies to entire spec)

> **DO NOT TRY TO BUILD EVERYTHING.**
>
> Judges are not using your product — they are evaluating your architecture, your demo, and your story. **A polished demo of 70% of this plan beats a buggy demo of 100% every single time.**
>
> Decide your exact demo flow in hours 0–2. Build to that flow. Don't deviate.

This rule supersedes everything below. Concretely, the spec is built in **4 strict layers** (see Section 8.5):

1. **Layer 1 — База** (H 0-7): the loop must work end-to-end on stubs
2. **Layer 2 — Улучшения базы** (H 7-13): real verification, rubric anchors light up. **Hard checkpoint at H 13.**
3. **Layer 3 — Wow** (H 13-16): only if Layer 2 green. Each Wow item has a slide/animation replacement.
4. **Layer 4 — Stretch** (H 16+): default = NOT BUILT. Only if Layer 3 fully shipped.

If you find yourself working on Layer 3 before Layer 2 is green: **stop**. The Wow features are designed to be replaceable with slides. The Base is not.

---

## ⚠ Stack Boundary — What Lives In Databricks, What Lives Outside

**Databricks is the data layer, not the application layer.** Use it for what it is best at, build the rest in Python + React for speed.

### ✅ Use Databricks ONLY for:

- **Data ingestion** — load 10k VF dataset into Bronze
- **Cleaning + structuring** — DLT Bronze → Silver → Gold (with LLM function calls in Silver for Data Cleaning, [F2])
- **Storing in Delta tables** — gold tables, atomic 4-way transaction, append-only outcome_feedback
- **Optional: embeddings** — Mosaic AI Vector Search for citation retrieval (Trial gives 1 endpoint, 1 VS unit, Delta-sync only — fits 10k facilities). Local FAISS index is the catastrophic-fallback if Vector Search storage-optimized index isn't enabled in our region.

### ❌ Do NOT use Databricks for:

- **Frontend** — use **React** deployed locally or on Vercel. No Databricks Apps / appkit SDK.
- **Agent logic** — use **Python + Databricks Foundation Model APIs (via `mlflow.deployments` client)** directly during MVP 1-3. External OpenAI/Anthropic SDKs are **fallback-only** (used if FM API catalog misses a model we need — see Section 12 fallback table). Mosaic AI Agent Framework / Knowledge Assistant / Genie Code are **Layer 4 stretch nice-to-haves** — added as thin-wrapper registration over the existing FastAPI service only if everything else green at H 16. They earn the "we use Agent Bricks" pitch line; they do not replace the underlying Python implementation.
- **Fast prototyping** — develop locally in Python; only push to Databricks when the data layer touches Delta.

### What this changes in the architecture

| Before stack boundary | After stack boundary |
|---|---|
| BookingAgent on Mosaic AI Supervisor | BookingAgent = FastAPI service + Databricks Foundation Model APIs (via `mlflow.deployments` client) for function calling |
| TriageAgent on Knowledge Assistant | TriageAgent = Databricks Foundation Model APIs call (Llama 3.3 70B) with corpus loaded in-memory |
| TrustScorer as UC functions | TrustScorer = Python module calling Databricks-hosted Llama (Extractor) + Databricks-hosted Claude (Validator) via `mlflow.deployments` client, reading from Delta |
| Validator inside UC functions | Validator = Python module (Databricks-hosted Claude via `mlflow.deployments`) reading rosters from Delta |
| RouterAgent = Genie Code | RouterAgent = pandas/SQL ranking over Gold |
| Frontend = Databricks App + appkit | Frontend = React app (Vercel deploy) reading from FastAPI + Delta REST API |
| Live MLflow Tracing as demo theatre | MLflow as **logger** only; trace data fetched via REST and rendered in our own UI |
| Lakehouse Monitoring drift panel as demo | Static screenshot in slide |
| Reasoning Panel SSE from Mosaic AI Supervisor | Reasoning Panel SSE from FastAPI BookingAgent |

### What stays Databricks-native (and is therefore precious demo material)

1. **DLT Bronze → Silver → Gold pipeline** — shown live in the pitch ("raw garbage in, clean intelligence out")
2. **Atomic 4-way Delta transaction** — 4-tile flip animation, the operational killer
3. **Mosaic AI Vector Search (optional, Trial-available)** — for embeddings + citation retrieval. Trial provides 1 endpoint with 1 VS unit and Delta-sync indexes only — enough for our 10k facilities. Local FAISS fallback if storage-optimized index unavailable in our region.
4. **Outcome feedback append + Reputation aggregation** — Delta time-aware queries, simple SQL

### Pitch frame change

**Old frame** (Tero's original spec): *"Databricks-native, every second something Databricks moves on screen."*

**New frame:** *"Databricks is the lakehouse spine — ingest, clean, structure, atomic-book, **and model-serve**. Python orchestration is the agentic glue. React is the surface. All inference runs on Databricks Foundation Model APIs — Llama 3.3 70B Extractor and Claude Opus 4.7 Validator — called via `mlflow.deployments` client. Each layer does what it is best at."*

This is more credible to judges who know real production architectures.

---

## 1. Executive Summary

A multi-agent healthcare intelligence system that turns 10,000 messy Indian hospital records into an operational brain. The core killer feature is **Verify-All-4 → Book-All-4 with the agents thinking visibly on screen**: confirm bed + oxygen + drug + specialist together (using two independent verification models), book them as one Delta-ACID atomic transaction, while a live reasoning panel exposes the agent chain-of-thought to judges.

**Five architectural choices that define this merge:**

1. **[T] Trust Layer is the operational killer** — not "find a hospital", but verify it across 4 dimensions and atomically reserve all 4. A 4-factor signal beats the bed-only ghost-bed dashboards that all decayed.
2. **[F1] Two independent models compute Trust, not one** — Extractor (Llama 3.3 70B) reads claims, Validator (Claude Opus 4.7) reads rosters/equipment and doubts them. **Both served by Databricks Foundation Model APIs** — no external API keys, no outbound whitelist risk, all inference inside the lakehouse. Disagreement *is* the verification signal. Different model families, disjoint retrieval — errors stop correlating.
3. **[T] Two-tier coverage with [F2] synthetic stream filling Tier-2** — Tier-1 (HAS-AGENT) gets real handshakes; Tier-2 (NO-AGENT) gets Predictor + a synthetic ±2-beds-per-5-min stream that makes the demo feel alive AND patches Tero's "Tier-2 is visually quiet" gap.
4. **[F2] Live Agent Reasoning Panel wraps the BookingAgent supervisor** — every step of Triage → TrustScorer → Validator → Router streams to a panel on screen. Judges *watch the AI think*. This is the visualisation that bridges Tero's operational depth and Friend 2's demo theatre.
5. **[T] Outcome Loop + Agent Reputation Score is the closer** — patient ping at T+2h retro-corrects Trust factors and Agent Reputation. *"First incentive system for honest healthcare data in India."* Single line that sells the whole system.

**Why this matches the brief:**

| Brief weight | Component covering it | Source |
|---|---|---|
| **35% Discovery & Verification** | Two-model TrustScorer + Validator + Outcome Loop + Agent Reputation | T + F1 |
| **30% IDP Innovation** | Per-field extraction with CI + click-to-source MLflow citations + DLT pipeline shown live | F1 + F2 |
| **25% Social Impact** | NGO Desert Dashboard (separate page) + Dead Zone overlay (toggle on hero map) | F1 + F2 |
| **10% UX/Transparency** | Live Reasoning Panel + click-to-source on every Trust factor | F2 + F1 |

**Conflict resolution log:**

| Conflict | Decision | Why |
|---|---|---|
| Atomic booking [T] vs Ola/Uber deeplinks [F2] | Keep atomic booking; deeplinks as **secondary buttons** on the same card | Atomic booking is the Grand Prize hook. Deeplinks degrade gracefully. |
| Voice MCP [T] vs Web Speech API [F2] | **Web Speech API as primary voice** (15 min); Voice MCP as Phase 3 stretch only | F2 is right — full Voice MCP is a 24h time-sink for a +2% rubric gain |
| Single-LLM extraction [T] vs Two-model Extractor/Validator [F1] | **F1 wins** — different models for independence | Cheap to build, kills Validator-correlation problem, sells better |
| Batch trust [F1] vs Real-time IntakeAgent [T] | **T wins** for Tier-1; **F1 batch is exactly Tier-2 mode** | Two-tier model already absorbs both |
| Single hero screen [F2] vs Three surfaces [T] | **Patient flow is hero**; Doctor copilot + NGO dashboard are tabs (one click away) | Hero discipline survives but doesn't kill rubric breadth |
| Mosaic AI Agent Framework [T] vs plain Python on Databricks Foundation Model APIs | **Python on FM APIs wins** — Agent Bricks Supervisor needs preview enablement + serverless budget policy + non-zero billing config even on Trial; agent logic is FastAPI service. **Models are still Databricks-hosted** (Llama + Claude via `mlflow.deployments`), so we keep the lakehouse-native rubric story. | Faster prototyping, no Public Preview risk on demo day, more honest production architecture, zero outbound network risk |
| Databricks Apps + appkit SDK [T] vs React on Vercel | **React on Vercel wins** | Judges click a real URL on Vercel, not a Databricks-hosted App that may auto-stop or hit Trial's outbound network limits. Frontend is decoupled from Databricks. |
| Genie Code RouterAgent [T] vs pandas/SQL ranking | **pandas/SQL wins** | Genie Code is available on Trial but Public Preview behaviour is unpredictable in a 24h window; pandas is dependable. Genie Code stays as Layer 4 stretch only — same demo line, lower risk. |

---

## 2. Architecture Diagram (merged + stack-split)

```
   ─────────── APPLICATION PLANE (Python + React, NOT Databricks) ───────────
                  ┌─────────────────────────────────────────┐
                  │  React App (Vercel deploy)               │
                  │  ├── Patient flow [HERO]  (web + voice)  │
                  │  ├── Doctor Transfer Copilot [tab]       │
                  │  └── NGO Desert Dashboard [tab]          │
                  │                                          │
                  │  >>> [F2] Live Agent Reasoning Panel <<< │
                  │       SSE consumer — real-time tokens    │
                  └────────────────────┬────────────────────┘
                                       │ HTTPS + SSE
                                       ▼
                  ┌─────────────────────────────────────────┐
                  │  [T] BookingAgent (FastAPI service)      │
                  │  Python + Databricks FM API function     │
                  │  calling (mlflow.deployments client).    │
                  │  Routes by intent. SSE every step.       │
                  │  MLflow as logger only (not live demo).  │
                  └──┬──────────┬───────────┬──────────┬─────┘
                     │          │           │          │
        ┌────────────▼──┐ ┌─────▼─────┐ ┌──▼────────┐ ┌▼─────────────┐
        │ TriageAgent   │ │TrustScorer│ │RouterAgent│ │ Validator    │
        │ [T]           │ │ [H]       │ │ [T]       │ │ [F1]         │
        │  Python +     │ │ Python +  │ │ pandas /  │ │ Python +     │
        │  Databricks   │ │ Databricks│ │ SQL over  │ │ Databricks   │
        │  FM API       │ │ FM API    │ │ Gold      │ │ FM API       │
        │  (Llama 3.3   │ │ Extractor │ │ Delta     │ │ (Claude      │
        │   70B)        │ │ (Llama)   │ │ table     │ │  Opus 4.7)   │
        │  symptom →    │ │   ⇄       │ │           │ │ doubts on    │
        │  specialty    │ │ Validator │ │           │ │ rosters/     │
        │  Vector       │ │ (Claude)  │ │           │ │ equipment    │
        │  Search OR    │ │ + per-fld │ │           │ │              │
        │  in-memory    │ │   CI [F1] │ │           │ │              │
        │  corpus       │ │           │ │           │ │              │
        └───────────────┘ └─────┬─────┘ └───────────┘ └──────────────┘
                                │
                ┌───────────────┼───────────────┐
                │               │               │
        ┌───────▼──────┐ ┌──────▼──────┐ ┌─────▼──────────┐
        │ TIER 1 [T]   │ │ TIER 2 [H]  │ │ TransferCoord  │
        │ HAS-AGENT    │ │ NO-AGENT    │ │ [T]            │
        │              │ │             │ │                │
        │ IntakeAgent  │ │ Predictor   │ │ atomic 4-way   │
        │ handshake    │ │ + [F2]      │ │ Delta txn      │
        │ (signed)     │ │ synthetic   │ │ + [F2] Ola/    │
        │              │ │ ±2/5min     │ │   Uber/108 as  │
        │ Trust ≤ 0.95 │ │ stream      │ │   secondary    │
        │              │ │ + voice     │ │   buttons      │
        │              │ │   fallback  │ │                │
        │              │ │ Trust ≤ 0.78│ │                │
        └──────┬───────┘ └──────┬──────┘ └────────┬───────┘
               │                │                  │
               └────────────────┼──────────────────┘
                                ▼
              ┌──────────────────────────────────────┐
              │  HANDSHAKE AUDIT + AGENT REPUTATION  │
              │  [T]                                  │
              │  • signature-verified handshakes      │
              │  • outcome-validated honesty          │
              │  → Agent Reputation Score             │
              └────────────────┬─────────────────────┘
                               ▼
              ┌──────────────────────────────────────┐
              │  OUTCOME LEARNING LOOP [T]            │
              │  • patient pinged 2h after routing    │
              │  • answer retro-corrects Trust [F1]   │
              │  • Predictor retrains on outcomes     │
              └──────────────────────────────────────┘

   ─────────── DATA PLANE (Databricks — this is what stays) ───────────
                  ┌─────────────────────────────────────────┐
                  │  Lakehouse (Delta + Unity Catalog)       │
                  │  bronze (raw 10k + VF schema)            │
                  │   → silver (geocoded, deduped, normed,   │
                  │      [F2] LLM function calls for cleaning)│
                  │   → gold (trust-scored, citation-ready)  │
                  │  + Mosaic AI Vector Search [Trial: 1 EP] │
                  │     local FAISS fallback if region-locked│
                  │  + Atomic 4-way Delta transaction        │
                  │     (the operational killer)             │
                  │  + outcome_feedback append + Reputation  │
                  │     aggregation (simple SQL)             │
                  │  + Virtue Foundation pydantic schema     │
                  │                                          │
                  │  Read by Python BookingAgent + sub-      │
                  │  agents via Databricks SQL Connector     │
                  │  / databricks-sdk.                       │
                  │                                          │
                  │  ✗ NO Mosaic AI Agent Framework          │
                  │  ✗ NO Genie Code (Layer 4 stretch only)  │
                  │  ✗ NO Databricks Apps SDK                │
                  │  ✗ NO Lakehouse Monitoring as live demo  │
                  │  (MLflow as logger OK; not as theatre)   │
                  └─────────────────────────────────────────┘
```

---

## 3. Components

Each component is tagged with provenance and a "[Cut if behind]" marker that fires when H 13 integration is not green.

### 3.1 BookingAgent (Supervisor)  **[T]**

- **Stack:** **Python FastAPI service + Databricks Foundation Model APIs** for function calling (via `mlflow.deployments` client — no external API keys, no outbound network risk, billed against Trial $400 credit). No Mosaic AI Agent Framework. SSE endpoint for Reasoning Panel. Reads/writes Delta via `databricks-sql-connector`.
- **Owner:** Tero
- **Folder:** `tero/supervisor/`
- **Routes by intent:**
  - Patient triage → Triage + TrustScorer + Validator + Router
  - Doctor transfer → Triage + TrustScorer + Validator + Router + TransferCoordinator
  - NGO desert query → pandas/SQL aggregation over Gold Delta (Genie Code is Layer 4 stretch — same UX, replaces our query writer with a managed agent)
- **Tier-1/Tier-2 routing:** for each candidate, checks IntakeAgent registration → yes: handshake; no: Predictor + synthetic stream + voice fallback
- **MLflow 3 tracing** enabled — every trace visible in dev panel
- **[F2] every step streams via SSE to Live Reasoning Panel** — agents thinking are visible end-to-end
- **Calls Atomic Booking transaction** when family taps Reserve
- **[Not cuttable]** — this is the orchestration core

### 3.2 TriageAgent  **[T]**

- **Stack:** **Python module calling Databricks Foundation Model APIs** (Llama 3.3 70B, via `mlflow.deployments` client) for function calling. Symptom→specialty corpus loaded in-memory from a JSON/YAML file (Trial-deployed Mosaic AI Vector Search is the optional upgrade path; Knowledge Assistant is *not* used because it requires non-zero serverless budget policy + Public Preview enablement, neither dependable in 24h).
- **Owner:** Mian
- **Folder:** `mian/triage/`
- **Indexed corpus:** symptom → specialty mappings, hospital capability docs, Hindi/English medical terms
- **Input:** free-text symptoms (Hindi or English)
- **Output:** `{ specialty, urgency, symptoms_parsed, confidence, trace_id }`
- **[F2] reasoning streams to panel** — first agent to fire, sets the visual rhythm
- **[Not cuttable]** — first stage of the pipeline

### 3.3 TrustScorer  **[H — Tero structure + Friend 1's two-model verification + Friend 1's per-field CI]**

The killer rubric component. Hybrid of all three sources.

- **Stack:** **Python module** with two LLMs running independently, **both served on Databricks Foundation Model APIs** via `mlflow.deployments` client — Extractor uses `databricks-meta-llama-3-3-70b-instruct`, Validator uses `databricks-claude-opus-4-7` (deliberately different model families: Meta vs Anthropic, on disjoint retrieval slices — error correlation is reduced, not eliminated; see "honest framing" below). Reads facility data from Delta via `databricks-sql-connector`. MLflow 3 as logger (not as live demo theatre). Mosaic AI Vector Search (Trial: 1 endpoint, Delta-sync) optional for retrieval; local FAISS fallback if storage-optimized index isn't enabled in our region. **Both LLMs run inside Databricks workspace — no external API keys, no outbound network whitelist required, inference billed against Trial $400 credit.**
- **Honest pitch framing (do not overclaim):** *"All clinical inference runs on Databricks Foundation Model APIs — facility notes and rosters never leave the lakehouse for an external LLM provider."* This is true. **What does leave** the lakehouse: derived trust scores, reasoning summary tokens (no raw PHI), and aggregate ranking data — flowing through our FastAPI service to the React frontend on Vercel. The patient's symptom transcript also passes through FastAPI (outside Databricks). If a judge asks pointedly about PHI in transit, the honest answer is *"raw clinical data stays in the lakehouse for inference; derived scores and the patient's typed symptom flow through our FastAPI orchestration layer, which is the standard pattern — same as any healthcare app calling an internal scoring service."* **Do not say "no PHI leaves the lakehouse" as an absolute** — that's overclaiming and a sharp judge will catch it.
- **Honest framing on two-model independence:** *"Different model families on disjoint retrieval slices reduce error correlation — they don't eliminate it."* Both models still read self-reported data from the same hospital (different columns, but one source of truth). A consistent liar can fool both. The verification value comes from catching **sloppy contradictions** (claim A without supporting structural evidence B) — not adversarial deception. Frame this honestly to ML-literate judges.
- **Owner:** Mian (Extractor + Validator + rule pack + data prep — full ownership)
- **Folder:** `mian/trust-scorer/`
- **What it does:** for each candidate hospital, computes 4-factor Trust:
  - `p_bed`, `p_oxygen`, `p_drug[specialty]`, `p_specialist[specialty]`
- **[F1] Two-model architecture (both on Databricks Foundation Model APIs):**
  - **Extractor** (`databricks-meta-llama-3-3-70b-instruct`) — reads notes/capability lists, emits claims with source-sentence indices
  - **Validator** (`databricks-claude-opus-4-7` — deliberately different model family) — reads rosters/equipment logs/pharmacy lists independently, doubts claims, emits per-field contradiction confidence
  - **Different retrieval slices** for each — Extractor sees facility narratives, Validator sees structured operational data. Errors stop correlating.
  - **Why both on Databricks**: zero outbound network risk on Trial workspace; single billing surface; rubric anchor — *"all clinical inference inside the lakehouse"* lands as governance/compliance signal for healthcare judges (the framing is **clinical inference**, not "all data movement" — see honest framing above).
- **[F1] Per-factor output with prediction interval and citation:**
  - Each factor returns `mean ± 95% CI` plus `evidence_completeness` score
  - Every value cites the exact source sentence (clickable in MLflow trace)
- **[T] Living Trust composition:** `trust = product(factors) × (1 - max(contradiction_confidence))` with confidence band; decays with data age
- **Output:**
  ```json
  {
    "hospital_id": "h_3421",
    "tier": 1,
    "factors": {
      "bed":        {"value": 0.94, "ci": 0.03, "verified_at": "2026-04-25T10:14Z", "source": "intake_agent",       "extractor_confidence": 0.96, "validator_contradiction": 0.0},
      "oxygen":     {"value": 0.98, "ci": 0.01, "verified_at": "2026-04-25T10:14Z", "source": "intake_agent",       "extractor_confidence": 0.99, "validator_contradiction": 0.0},
      "drug":       {"value": 0.91, "ci": 0.04, "citation":   "facility_note_p3_s4", "source": "extraction+validator","extractor_confidence": 0.94, "validator_contradiction": 0.05},
      "specialist": {"value": 0.18, "ci": 0.05, "citation":   "facility_note_p1_s2", "source": "extraction+validator","extractor_confidence": 0.88, "validator_contradiction": 0.92, "flag": "no_anesthesiologist"}
    },
    "trust": 0.16,
    "trust_ci": 0.06,
    "decay_per_hour": 0.04,
    "evidence_completeness": 0.85,
    "trace_id": "tr_xyz"
  }
  ```
- **[F1] Click-to-source MLflow trace:** every factor → exact sentence highlighted in original note + counter-evidence row in roster. **The rubric click**.
- **Sentence pre-indexing (deterministic citation, not LLM-emitted byte offsets):** in DLT Silver, facility notes are split into sentences by a `nltk.sent_tokenize()` step and stored in a `silver_facility_sentences` Delta table with stable IDs of the form `{hospital_id}_p{paragraph_idx}_s{sentence_idx}` (e.g. `h_3421_p3_s4`). Roster rows already have stable `roster_row_44` IDs from the source ingestion. The Extractor and Validator prompts include the sentence/row IDs alongside the text and are instructed to emit the ID of the supporting/contradicting sentence in their structured output (`{"claim": "...", "citation_id": "h_3421_p3_s4"}`). **Click-to-source is then a lookup, not a retrieval** — the React modal calls `GET /trace/{trust_score_id}` which returns `{citation_id, sentence_text, hospital_note_excerpt, counter_row_id, counter_row_text}` — frontend just highlights. If the LLM emits an invalid `citation_id` (rare on temperature 0), the modal shows "source unverified" rather than fabricating.
- **Reference call shape (Databricks-hosted, no external SDK):**
  ```python
  import mlflow.deployments
  from databricks import sql

  client = mlflow.deployments.get_deploy_client("databricks")

  # Extractor (Llama)
  extractor_resp = client.predict(
      endpoint="databricks-meta-llama-3-3-70b-instruct",
      inputs={
          "messages": [
              {"role": "system", "content": EXTRACTOR_PROMPT},
              {"role": "user", "content": facility_notes_text},
          ],
          "temperature": 0.0,
      },
  )

  # Validator (Claude — different family, disjoint retrieval slice)
  validator_resp = client.predict(
      endpoint="databricks-claude-opus-4-7",
      inputs={
          "messages": [
              {"role": "system", "content": VALIDATOR_PROMPT},
              {"role": "user", "content": roster_and_equipment_text},
          ],
          "temperature": 0.0,
      },
  )

  # Read source data + write Trust scores back, all via SQL connector
  with sql.connect(server_hostname=..., http_path=..., access_token=...) as conn:
      with conn.cursor() as cur:
          cur.execute("SELECT * FROM main.healthcare.gold_hospitals WHERE id = ?", [hospital_id])
          ...
  ```
- **[Not cuttable]** — this *is* the rubric anchor

### 3.4 BedPredictor (Tier 2 only)  **[T]**

- **Stack:** **Python sklearn model serialized with joblib**, served by a FastAPI endpoint co-located with BookingAgent. MLflow as logger only (not live demo theatre). Reads training data from Delta.
- **Owner:** Mian
- **Folder:** `mian/predictor/`
- **Used only for Tier 2 hospitals** (no IntakeAgent)
- **[F2] hooked into the synthetic stream** — predictor consumes `±2 beds / 5 min` updates as live signal, not just historical baseline
- **[Cut if behind]** — degrades gracefully to history-only baseline; the synthetic stream alone suffices for visual aliveness

### 3.5 RouterAgent  **[T] — pandas/SQL primary, Genie Code Layer 4 stretch only**

- **Stack:** **Python module + pandas + SQL** ranking over Gold Delta table (read via `databricks-sql-connector`). Genie Code is available on Trial but moved to **Layer 4 stretch only** — Public Preview behaviour and SQL latency on the trial 50-DBU/h warehouse are unpredictable in a 24h window. pandas is dependable.
- **Owner:** Tero
- **Folder:** `tero/router-config/`
- **What it does:** ranks candidates by Trust × Reputation × travel × cost. Output streams to Reasoning Panel via SSE.
- **Genie Code as Layer 4 stretch:** if everything else green, plug Genie Code in for the multi-step demo query *"rural Bihar appendectomy with part-time doctors"*. Pre-recorded fallback ready.
- **[Cut if behind]** — pandas/SQL is the primary path. Genie Code is gravy.

### 3.6 TransferCoordinator + Atomic Booking  **[T] + [F2 deeplinks as secondary]**

- **Stack:** **Python module + single-row Delta INSERT into `atomic_bookings` table** via `databricks-sql-connector`. The 4 reservations live as **struct columns in one row** (not 4 separate INSERTs into 4 separate tables). Single-row write to a Delta table is atomic by definition — that's the only ACID guarantee `databricks-sql-connector` provides at the SQL layer (no `BEGIN TRANSACTION` across tables; auto-commit per statement). All side effects (mock 108/ABDM/IntakeAgent/pharmacy) are validated via **synchronous HTTP probes BEFORE the INSERT** — if any probe fails, no row is written, no rollback needed.
- **Owner:** Tero (transaction layer) + Mian (FHIR + packet)
- **Folder:** `tero/transfer/` + `mian/transfer/`
- **[T] Atomic booking — corrected architecture:**
  1. **Pre-validation phase** (parallel HTTP, ~200ms total):
     - Probe `bed_reserve` mock endpoint (port 9101) — `200 OK` or `409 Conflict`
     - Probe `ambulance_dispatch` mock endpoint (port 9102) — `200 OK` or `503`
     - Probe `doctor_slot_hold` mock endpoint (Tier 1 = real IntakeAgent on 9201/9202/9203, Tier 2 = mock 9103) — yes/no
     - Probe `drug_reserve` mock endpoint (port 9104) — `200 OK` or `409 stockout`
  2. **Decision:** if ALL 4 probes succeed → step 3. If ANY fails → return `{atomic_txn_id: null, rollback_reason: <which>, factors_locked: []}` — no Delta write. Auto-suggest second-ranked hospital.
  3. **Single-row INSERT** into `atomic_bookings` (UC-managed Delta table):
     ```sql
     INSERT INTO main.healthcare.atomic_bookings (
       txn_id, hospital_id, patient_session_id, ts,
       bed_reservation, ambulance_dispatch,
       doctor_slot, drug_reservation
     ) VALUES (?, ?, ?, current_timestamp(),
       struct(?, ?, ?),  -- bed: {reservation_id, ward, eta_min}
       struct(?, ?),     -- ambulance: {dispatch_id, eta_min}
       struct(?, ?),     -- doctor: {slot_id, doctor_name}
       struct(?, ?)      -- drug: {lock_id, sku}
     )
     ```
  4. **Confirmation phase** (parallel commit pings to mock side-effect endpoints) — fire-and-forget; if any side effect rejects post-INSERT, log to `atomic_bookings_compensation` for manual reconciliation (real-world parity, not in demo). For demo: probes are deterministic mocks, this never fires.
- **Why this is honest about Delta semantics:** `databricks-sql-connector` auto-commits per statement; cross-table multi-statement transactions are not supported the way Postgres `BEGIN/COMMIT` works. A **single-row write is the atomic unit Delta provides at the SQL layer**. We get the same guarantee (all-or-nothing visible to readers) by collapsing the 4 reservations into one row with struct columns. The pitch line *"Delta ACID atomic 4-way booking"* still holds because **the row IS the transaction** and serves as the single source of truth that the 4 mock side effects reconcile against.
- **Demo failure-and-retry script** (mocks deliberately seeded to fail on Hospital A's drug probe): family taps Reserve A → drug probe returns `409 stockout` → no Delta INSERT, all 4 tiles flash red → BookingAgent auto-suggests Hospital B → 4 probes pass → single-row INSERT → all 4 tiles flip green simultaneously.
- **For Tier 1 hospitals** the IntakeAgent confirms `doctor_slot_hold` through real handshake; **for Tier 2** mock endpoints simulate.
- **Doctor copilot extension:** generates FHIR snippet + PDF referral packet + D2D handoff form (separate, not part of atomic write).
- **[F2] Secondary deeplink buttons on each card:** Ola/Uber/108 — for "I want to handle transport myself" path.
- **[Visual demo]:** 4 tiles flip green simultaneously on successful single-row INSERT; flash red on any pre-validation failure. The animation reads the 4 struct columns from the just-written row. **Not cuttable** — this is the operational killer demo moment.

### 3.7 IntakeAgent (Tier 1, hospital-side)  **[T]**

- **Stack:** **Lightweight Python FastAPI server** with mock signature header. No MCP server, no UC signed identity (those were Layer 3 polish). Deployed locally for demo.
- **Owner:** Mian (agent expertise)
- **Folder:** `mian/intake-agent/`
- **What it does:**
  - Reads from hospital's HMIS / pharmacy ERP / staff scheduling (or mocks if hospital has none)
  - Exposes structured yes/no MCP endpoints: `bed_available?`, `drug_in_stock?`, `specialist_on_shift?`, `oxygen_working?`
  - Signs every response with hospital's UC identity (auditable)
- **For demo:** 2-3 hospitals fake-onboarded as Tier 1; rest fall through to Tier 2
- **Pitch story:** scaling argument — onboarding is self-incentivized (Tier 1 ranks higher, attracts more patients)
- **[Cut if behind]** — all hospitals can fall back to Tier 2 mode (synthetic stream + predictor); Tier 1 demo is pre-recorded fallback

### 3.8 Synthetic Live Stream (Tier 2 hero feature)  **[F2]**

- **Stack:** **Python script** running in a local cron OR as a Databricks scheduled job — either works. Appends to Delta via `databricks-sql-connector`. Broadcasts updates to React frontend via FastAPI WebSocket / SSE channel.
- **Owner:** Tero (script) + Mian (Delta plumbing)
- **Folder:** `tero/sim-stream/`
- **What it does:**
  - Picks ~30 random rows in Tier 2 (no IntakeAgent) facilities
  - For each: `bed_count = max(0, bed_count + randint(-2, +2))`
  - 5% chance: flip `icu_full = True`
  - Appends update row → Gold materialized view recomputes → map repaints
- **[F2] Demo discipline:** time the next tick to land mid-pitch — pin shifts color visibly. *"And there it is — bed count just dropped at Hospital X."*
- **Pitch line (verbatim from F2):** *"In production this connects to IVR systems. In our demo we simulate the pipeline to show the architecture. Judges respect this."*
- **[Cut if behind]** — degrade to manual button "force tick" in dev panel; pre-record pin animation

### 3.9 Voice Input — Two-Mode  **[H — F2 primary, T as Phase 3 stretch]**

- **Owner:** Arushi (Web Speech) + Tero (Voice MCP if reached)
- **Folder:** `arushi/voice-input/`, `tero/voice/`
- **Mode A (primary, ALWAYS BUILT):** **[F2] browser Web Speech API** — Hindi/English, 15-min add. Fires on user mic-click in patient flow. Transcript appears in chat → BookingAgent processes.
- **Mode B (Phase 3 stretch only, if ALL Mode A green):** **[T] Voice MCP** — Fish Audio TTS + OpenAI gpt-4o-audio + Realtime function calling. Fires only for Tier 2 + min(factor_confidence) < 0.7 + patient on the road. Outbound call to hospital, not user input.
- **Demo discipline:** Mode A is the demo voice path. Mode B is "if we hit it, bonus pitch line; if not, doesn't break demo."
- **[Mode B Cut by default]** — if Tero's load is at risk, drop entirely

### 3.10 Live Agent Reasoning Panel  **[F2]**

- **Stack:** **FastAPI SSE endpoint on BookingAgent → React EventSource consumer**. No Databricks involvement.
- **Owner:** Arushi (UI) + Tero (streaming wiring)
- **Folder:** `arushi/reasoning-panel/`
- **What it shows:** every reasoning token from each agent labelled by agent:
  - 🩺 Triage: "swollen feet + dyspnea → CHF, cardiology primary, pulmonology secondary, urgency HIGH"
  - 🔍 TrustScorer: "querying 247 candidates → Extractor pass → Validator pass → 4-factor compose"
  - 🛡 Validator: "Hospital C: claims Advanced Surgery, no Anesthesiologist on roster → contradiction 0.92, demote"
  - 🗺 Router: "ranking by Trust × Reputation × travel × cost"
  - 🚑 TransferCoordinator: "atomic booking 4-way commit"
- **[F2] Demo rule:** the panel must be visibly streaming during every second of live demo. Stale panel = wasted demo seconds.
- **[Not cuttable]** — this is the visualisation that bridges all three plans

### 3.11 Outcome Learning Loop  **[T]**

- **Stack:** **Python module** with a simple cron (or local timer for demo). Appends `outcome_feedback` rows to Delta. Trust factor retro-correction is a SQL update on Gold. UI playback animation is React-side. **No real Twilio/SMS/WhatsApp** in scope.
- **Owner:** Tero + Mian
- **Folder:** `tero/outcome-loop/`
- **Flow:**
  1. Patient routed to Hospital X at T=0
  2. T+2h: SMS / WhatsApp ping: "Did Hospital X have what we said? bed/drug/specialist y/n"
  3. Answer logged in `outcome_feedback` Delta table
  4. If outcome diverges from prediction → Trust factor retro-corrected, Predictor retrained, Agent Reputation updated
- **For demo:** time-warp simulation — replay historical "outcomes" in fast-forward, show retro-correction live
- **[Cut if behind]** — keep the schema and one playback animation; drop real scheduled job

### 3.12 Agent Reputation Score  **[T]**

- **Stack:** **Simple Delta SQL aggregation** (`honest / total handshakes`). Pre-rendered React animation shows the score ticking down for one hospital during demo. Lakehouse Monitoring is available on Trial and would visualise this drift natively, but the stack split keeps it as a **static screenshot in the slide** — switching to a live Databricks dashboard mid-demo breaks the React-app narrative and adds a tab-switching seam.
- **Owner:** Tero
- **Folder:** `tero/reputation/`
- **Per-hospital score:**
  ```
  Hospital A IntakeAgent:
    Total handshakes: 1,247
    Confirmed honest: 1,189 (95.3%)
    Confirmed dishonest: 58 (4.7%)
    → Agent Reputation Score: 0.953
    → Trust ceiling: 0.95 × 0.953 = 0.905
  ```
- **Pitch line:** *"First incentive system for honest healthcare data in India."*
- **[Cut if behind]** — keep one screenshot + one pitch line; drop live aggregation

### 3.13 NGO Desert Dashboard  **[F1] + [F2 dead-zone overlay]**

- **Stack:** **React page (tab in main app, deployed on Vercel)** + Leaflet/Mapbox heatmap + REST endpoint on BookingAgent that returns aggregated PIN × specialty counts from Gold. No Databricks Apps SDK, no Genie Code.
- **Owner:** Arushi
- **Folder:** `arushi/ngo-dashboard/`, `arushi/dead-zone-overlay/`
- **Two surfaces:**
  - **[F1] Separate page:** map of India by PIN, layered with Trust scores and capability gaps. Filter by specialty (dialysis, oncology, trauma) and minimum trust threshold.
  - **[F2] Dead Zone toggle on hero map:** same data, visible on the patient-flow map as a togglable red overlay — judges see problem and solution simultaneously.
- **Demo line:** *"Bihar — 4 districts, 0 dialysis facilities in 200km radius, highest Oncology gap by PIN."*
- **Brief weight:** 25% Social Impact
- **[Not cuttable]** — quarter of the rubric

### 3.14 Validator Agent (anti-hallucination)  **[F1] (extends T's Validator role)**

- **Stack:** The Validator role is **subsumed into TrustScorer's two-model architecture** — there is no separate Validator pass. Each TrustScorer factor IS extractor+validator output composed.
- **Owner:** Mian (lives inside `mian/trust-scorer/`)
- **What it does:** the Validator model (Claude) emits per-field contradiction confidence as part of TrustScorer output. Cross-rules:
  - "Advanced Surgery claimed but no Anesthesiologist listed" → flag confidence 0.92
  - "ICU claimed but no ventilators in equipment log" → flag 0.6
  - "24/7 availability claimed but no night-shift staff" → flag 0.88
- **Why merged into TrustScorer:** in F1's spec, Validator is a separate component. In this merge, it lives inside TrustScorer because they are the same model running on the same row at the same time. Reduces contract surface, no behavior loss.

### 3.15 Frontend App (UI)  **[H]**

- **Stack:** **React (Vite or Next.js) deployed on Vercel** + Leaflet/Mapbox + EventSource for SSE + native `fetch` for REST. **No Databricks Apps SDK, no appkit.** Vercel URL in pitch deck.
- **Owner:** Arushi
- **Folder:** `arushi/app/`
- **[F2] Hero discipline applied:** Patient flow is the main page. Doctor copilot and NGO dashboard are tabs (one click away), not separate URLs.
- **Patient flow [F2 + T]:**
  - Voice + text input (Hindi/English)
  - Map of India with color-coded pins + Dead Zone overlay toggle
  - **[F2] Live Agent Reasoning Panel** on the side
  - 3 facility cards with: 4-factor Trust + CI + click-to-source + atomic-book button + secondary Ola/Uber/108 deeplinks
- **Doctor Transfer Copilot [T] (tab):**
  - Sending hospital → 3 receiving recommendations with Trust + Reputation badges → referral packet preview → ambulance ETA
- **NGO Desert Dashboard [F1] (tab):**
  - PIN-code map of medical deserts
- **[F2] Genie Code chat embedded** for live judge queries

### 3.16 Data Plane (Databricks — this is where it lives)  **[H]**

This is the only place Databricks runs. Everything else is Python + React.

- **[T] Lakeflow / DLT** medallion pipeline:
  - **Bronze:** raw 10k records + Virtue Foundation Schema column mapping
  - **Silver:** normalized addresses (geocoded), deduped, specialty taxonomy mapped, factor extractions, **[F2] LLM function calls inline for Data Cleaning** (this is where Databricks Model Serving earns its demo moment)
  - **Gold:** Trust-scored (written by external Python TrustScorer service), **[F1] citation-indexed**, ready for routing/desert queries
- **[OPTIONAL] Mosaic AI Vector Search:** indexes hospital descriptions + symptom→specialty corpus + facility-note sentences for citation. Trial provides 1 endpoint with 1 VS unit (Delta-sync only — Direct Vector Access is not supported even on Trial). **Local FAISS index built from Gold is the catastrophic fallback** if storage-optimized index isn't enabled in our region or the trial endpoint is misconfigured.
- **Atomic 4-way Delta transaction:** the operational killer; written by Python TransferCoordinator via SQL connector
- **outcome_feedback append + Reputation aggregation:** simple Delta SQL
- **MLflow as logger only:** runs hosted in Databricks; trace data fetched by Python via REST and rendered in our own React UI for click-to-source
- **Unity Catalog:** kept simple — one catalog, governance left at default for hackathon
- **Virtue Foundation pydantic schema:** imported into `contracts/schemas.py` — this drives both Python services and frontend types

**Removed from data plane** (was in earlier merge versions): Mosaic AI Agent Framework, Genie Code (Layer 4 stretch only), Lakehouse Monitoring as live demo, MLflow live tracing as theatre, Online Tables (overkill — Gold reads at query time are fast enough on demo size), Unity Catalog signed identity for IntakeAgent (mock signature).

---

## 4. Data Flow — The Killer (Verify-All-4 → Book-All-4 with reasoning visible)

This is the demo's hero flow. Combines Tero's Verify-All-4 + Atomic Booking with Friend 1's two-model verification and Friend 2's live reasoning panel.

```
[Family via React App on Vercel] taps mic, speaks: «बुखार और सीने में दर्द, पटना»
    │  [F2] Web Speech API → Hindi transcript appears in chat
    │
    ▼
[BookingAgent] receives intent: triage_route
    │  [F2] supervisor opens SSE stream → Reasoning Panel goes live
    │
    ├─▶ TriageAgent
    │     PANEL 🩺 "fever + chest pain, location Patna"
    │     PANEL 🩺 "specialty: cardiology, urgency: 3"
    │     ──▶ {specialty: cardiology, urgency: 3}
    │
    ├─▶ TrustScorer (per candidate)
    │     PANEL 🔍 "247 candidates within 50km radius"
    │     PANEL 🔍 "running Extractor (Databricks-hosted Llama 3.3 70B) over notes..."
    │     PANEL 🛡 "running Validator (Claude) over rosters..."
    │     │
    │     ├─ Tier 1 (HAS-AGENT) → handshake IntakeAgent [T]
    │     │     ├─ "bed?" "yes" (signed)
    │     │     ├─ "oxygen?" "yes"
    │     │     ├─ "clopidogrel?" "yes"
    │     │     └─ "cardiologist on shift?" "yes"
    │     │     PANEL 🤝 "Hospital A handshake: 4/4 yes (signed by hospital UC identity)"
    │     │     → Trust 0.95 ± 0.02 (signed, fresh)
    │     │
    │     ├─ Tier 2 (NO-AGENT) → Predictor + synthetic stream + Extractor⇄Validator [H]
    │     │     ├─ p_bed = 0.72 ± 0.11 (predictor + synthetic stream tick T-3min)
    │     │     ├─ p_oxygen = 0.83 (Extractor confident, Validator no contra)
    │     │     ├─ p_drug = 0.65 (Extractor 0.78, Validator contra 0.18, age 4h)
    │     │     ├─ p_specialist = 0.78 (Extractor confident, Validator no contra)
    │     │     PANEL 🛡 "Hospital B: no contradictions on rosters"
    │     │     → Trust 0.42 ± 0.18
    │     │     │
    │     │     └─ if min(ci) < 0.7 AND patient on road AND Mode B built:
    │     │            └─▶ Voice MCP outbound (rare)
    │     │
    │     └─▶ Validator (inside TrustScorer) cross-checks Tier 1 too
    │            PANEL 🛡 "Hospital C: claims Advanced Surgery"
    │            PANEL 🛡 "Hospital C: roster_row_44 — no Anesthesiologist on shift"
    │            PANEL 🛡 "Hospital C: contradiction confidence 0.92 — DEMOTE"
    │            ──▶ Hospital C demoted, Trust 0.16 ± 0.06, flag visible
    │
    ├─▶ RouterAgent (pandas/SQL ranking — Genie Code is Layer 4 stretch)
    │     PANEL 🗺 "ranking by Trust × Reputation × travel × cost"
    │     ──▶ Hospital A first, B second, C visible-but-flagged
    │
    └─▶ BookingAgent returns:
          Hospital A   4/4 ✓   Trust 0.95 ± 0.02   verified live (Tier 1)
          Hospital B   3/4 ⚠   Trust 0.42 ± 0.18   stream-fresh
          Hospital C   ⚠ flag  Trust 0.16          (no Anesthesiologist)

[Family taps "Reserve A"]
    │
    ▼
[TransferCoordinator] starts ATOMIC BOOKING (single Delta row, struct columns):
    PANEL 🚑 "pre-validating 4 sub-systems in parallel..."
    │
    ├─ HTTP probe bed_reserve (port 9101)        → 200 OK
    ├─ HTTP probe ambulance_dispatch (port 9102) → 200 OK
    ├─ HTTP probe doctor_slot_hold (port 9103)   → 200 OK
    ├─ HTTP probe drug_reserve (port 9104)       → 409 stockout
    └─ Pre-validation FAILED → no Delta write, no rollback needed
    PANEL 🚑 "drug stockout on Hospital A — no commit"
    │  [Visual] all 4 tiles flash red, reset to grey
    ▼
[BookingAgent] auto-suggests Hospital B:
    PANEL 🤖 "auto-suggest Hospital B — note: lower drug confidence"
    ├─ probes: 4/4 OK
    └─ INSERT single row into atomic_bookings(bed, ambulance, doctor, drug as structs) → COMMIT
    │  [Visual] all 4 tiles flip green simultaneously (one row, 4 struct columns)
    ▼
[Confirmation card] ETA 23 min, Dr. Sharma waiting, drug ready
    + [F2] secondary buttons: [Call ambulance 108]  [Ola]  [Uber]
    + [F1] click any factor → MLflow trace → exact source sentence

   ─── 2 hours later (or time-warp simulation in demo) ───
[Outcome Loop] WhatsApp ping: "Was the bed/drug/specialist actually there?"
    │
    ├─ Patient: "no clopidogrel arrived 30min late"
    ▼
[Reputation Score] Hospital B IntakeAgent score drops 0.91 → 0.87
    PANEL 📊 "Hospital B Reputation: 0.91 → 0.87"
[TrustScorer] retroactively retrains drug factor for Hospital B
[MLflow logger] drift event recorded → fetched by Python service for trace UI
                (Lakehouse Monitoring would visualise this on Trial; demo uses static slide instead per stack split)
```

**Demo theatre annotations** (every line in the panel = one moving thing on screen):
1. Voice transcript appears in chat
2. Reasoning panel streams Triage → Extractor → Validator → Router
3. Validator demotes Hospital C visibly
4. Reserve tap → 4 tiles attempt → rollback (red flash) → retry → commit (green flip)
5. Atomic-booking confirmation card with Ola/Uber/108 buttons
6. (Time-warp) Outcome ping → Reputation score ticks down

---

## 5. Data Flow — Transfer Copilot (Doctor tab)

Lifted essentially unchanged from Tero's spec, with Reasoning Panel wrapping.

```
[Doctor via React App on Vercel] selects "Transfer patient from St. John's"
    │  [F2] Reasoning Panel opens
    │
    ▼
[BookingAgent] receives intent: transfer_coordinate
    │
    ├─▶ TriageAgent
    │     PANEL 🩺 "tertiary specialty needed: cardiothoracic surgery"
    │
    ├─▶ TrustScorer (Extractor⇄Validator over candidates)
    │     PANEL 🔍🛡 "3 candidate receivers each with 4-factor trust"
    │
    ├─▶ Validator (inside TrustScorer)
    │     PANEL 🛡 "no contradictions on top 3"
    │
    ├─▶ RouterAgent
    │     PANEL 🗺 "ranked by capability + Trust + travel"
    │
    └─▶ TransferCoordinator
          │
          ├─ generates FHIR snippet + PDF referral packet
          ├─ atomic-books receiver bed + ambulance + receiving-doctor slot
          ├─ opens D2D handoff form
          └─ returns aggregated packet
                │
                ▼
[App] renders: 3 receivers card + Trust badges + packet preview + ambulance ETA + D2D form
```

---

## 6. Data Flow — Outcome Loop + Agent Reputation

```
T=0    Patient routed to Hospital X. Trust 0.94. Logged.
T+2h   Outcome ping: "Did X have bed/drug/specialist as we said?"
T+2h+ε Patient answers yes/no per factor.

       For each factor where patient says NO:
         ├─ Trust factor for that hospital retro-corrected
         ├─ if Tier 1 (HAS-AGENT): IntakeAgent handshake flagged "dishonest"
         │     └─ Agent Reputation Score updated:
         │           reputation = honest_handshakes / total_handshakes
         │           Trust ceiling adjusted to max × reputation
         ├─ if Tier 2 (NO-AGENT): Predictor / extraction model gets retraining signal
         │     └─ MLflow 3 logs new run; drift visualisation rendered in our React UI
         │       (Lakehouse Monitoring is the Trial-native alternative — kept as static slide per stack split)
         └─ Future patients see updated Trust automatically

Two hospitals after 1000 patients:
  Hospital A — Reputation 0.95 (188 dishonest of 1000)
  Hospital B — Reputation 0.62 (380 dishonest)
  → Hospital A's max Trust 0.95 × 0.95 = 0.9025
  → Hospital B's max Trust 0.95 × 0.62 = 0.589 — drops in ranking automatically
```

**Pitch line (carried verbatim from T):** *"We built an incentive system. Hospitals that lie through their agent are auto-demoted. First time honest data is more valuable than gaming the dashboard."*

---

## 7. Integration Contracts

Each agent emits a fixed JSON shape. Supervisor parses, validates with Pydantic. **VF Schema is the base** (`from contracts.schemas import ...`).

```
TriageAgent.output    → { specialty, urgency, symptoms_parsed, confidence, trace_id }
TrustScorer.output    → { hospital_id, tier, factors{bed,oxygen,drug,specialist with extractor_confidence + validator_contradiction + ci + citation}, trust, trust_ci, decay_per_hour, evidence_completeness, trace_id }
                        # [F1] each factor carries both extractor and validator outputs
BedPredictor.output   → { predictions[{hospital_id, p_bed, ci, age_min}], model_version, trace_id }
RouterAgent.output    → { ranked[{hospital_id, name, travel_min, specialty_match, cost_inr, non_medical_inr}], genie_query_id }
TransferCoord.output  → { receivers, referral_packet_url, fhir_snippet, ambulance_eta_min, atomic_txn_id, factors_locked[],
                          deeplinks{ola_url, uber_url, ambulance_number} }
                        # [F2] deeplinks added as secondary path
IntakeAgent.handshake → { hospital_id, query, response, signature, latency_ms, agent_version }
SyntheticStream.event → { hospital_id, beds_delta, icu_full, ts }
                        # [F2] new contract — synthetic stream events drive Tier-2 freshness
VoiceMCP.output       → { hospital_id, factor, verified_value, raw_transcript, audio_url, mode_used }
                        # [T] Mode B only, optional
WebSpeechInput        → { transcript, language_detected, confidence }
                        # [F2] frontend → BookingAgent (no separate JSON contract — passes through chat input)
OutcomeFeedback.input → { patient_id, hospital_id, factor, actual_value, timestamp }
ReasoningPanel.event  → { agent: "triage"|"extractor"|"validator"|"router"|"transfer"|"reputation",
                          token, trace_id, ts }
                        # [F2] new contract — SSE stream from supervisor to UI
                        # NOTE: extractor + validator are emitted as SEPARATE event types
                        # (matches MVP 2 sse_real.py which color-codes them distinctly).
                        # "trust_scorer" is the logical parent — never emitted as an event;
                        # frontend groups extractor+validator events under the trust_scorer
                        # section of the panel.
```

**Integration day** (last 4-6 hours):
1. Supervisor stub already exists with mocked sub-agent calls
2. Each owner replaces their mock with real implementation by emitting matching JSON
3. Each owner runs `pytest contracts/test_my_output.py` — output matches Pydantic schema
4. End-to-end test on demo dataset
5. Demo theatre rehearsal

---

## 8. Team Mapping — 3 People, Parallel Folders

**Team:** Tero, Mian, Arushi. Mian absorbs the previous Mubarak + Danish split (full backend ownership). Folder discipline is strict — **no overlapping ownership in the same folder**, so all three can work in parallel without merge conflicts.

| Person | Role | Owns | Project Folder | Stack |
|---|---|---|---|---|
| **Tero** | Orchestration + integration + demo lead | BookingAgent (FastAPI) + SSE wiring to frontend + Atomic Booking + RouterAgent + Synthetic Live Stream + Outcome Loop + Reputation aggregation + integration + demo theatre + pitch deck | `tero/supervisor/`, `tero/transfer/`, `tero/router/`, `tero/sim-stream/`, `tero/outcome-loop/`, `tero/reputation/`, `tero/integration/` | **Python, FastAPI, Databricks Foundation Model APIs (`mlflow.deployments`), `databricks-sql-connector`, Delta ACID, SSE** |
| **Mian** | Backend + data + agent logic lead | DLT Bronze→Silver→Gold pipeline + TriageAgent + two-model TrustScorer (Extractor + Validator) + IntakeAgent (Tier-1 mocks) + Validator rule pack + BedPredictor + Dead Zone aggregation + Hindi prompt content | `mian/dlt-pipeline/`, `mian/triage/`, `mian/trust-scorer/`, `mian/intake-agent/`, `mian/validator-rules/`, `mian/predictor/`, `mian/dead-zones/` | **Lakeflow/DLT (Databricks-side), Python, Databricks Foundation Model APIs via `mlflow.deployments` (Llama 3.3 70B + Claude Opus 4.7), MLflow as logger, FastAPI mock servers, sklearn, FAISS or Mosaic Vector Search** |
| **Arushi** | Frontend lead + submission | React app (Patient flow HERO + tabs) + Reasoning Panel (EventSource SSE) + 4-tile flip animation + voice input + click-to-source modal + NGO Desert Dashboard tab + Dead Zone overlay + submission package | `arushi/app/`, `arushi/reasoning-panel/`, `arushi/voice-input/`, `arushi/ngo-dashboard/`, `arushi/dead-zone-overlay/`, `arushi/submission/` | **React (Vite or Next.js) on Vercel, Leaflet/Mapbox, EventSource, native fetch, Web Speech API** |

### Load distribution

| Person | Approx. hours | Risk |
|---|---|---|
| **Tero** | ~17h | High — orchestrator + transactional core + integration. Pitch + demo also on him. |
| **Mian** | ~17h | **Critical** — broadest scope (data pipeline + agent logic + Tier-1 mocks). Single point of failure for backend. Mitigation: stub gold table H 1, single-model TrustScorer in MVP 1, two-model in MVP 2, IntakeAgent in MVP 3. |
| **Arushi** | ~13h | Medium — narrower scope (frontend only) but on the demo critical path. Reasoning Panel + 4-tile flip + click-to-source modal are the three killer-anchor visuals. |

### Folder boundary rules

1. **Never edit another owner's folder** — open a PR / commit a contract example instead.
2. **All cross-folder integration goes through `contracts/schemas.py`** (committed by Tero in MVP 0).
3. **Mock JSON outputs in `mocks/`** — every owner commits a sample JSON for their endpoint at the start of each MVP, so others can build against it without waiting.
4. **Daily merges** — every MVP boundary requires a clean integration test on the main branch before the next MVP starts.

### Communication discipline (3 people, no slack)

- **15-min standup at every MVP boundary** (H 7, H 13, H 19) — what shipped, what blocked, what's next
- **Demo flow document** in `docs/demo-script.md` (Tero owns) is the single source of truth — never deviates from H 0-2 lock

---

## 8.5 Priority Tiers — What Is Base, What Is Wow

Every component is assigned to one of 4 layers. **Build order is strictly layer-by-layer**. Do not start Layer 2 before Layer 1 is green. Do not touch Layer 3 before Layer 2 hard checkpoint at H 13 passes.

### LAYER 1 — База (must work to have a demo at all)

If any of these is broken at H 13, freeze everything else and fix.

| Component | Owner | Stack | Why base |
|---|---|---|---|
| Stub gold table (50 hardcoded hospitals) | Mian | Delta + databricks-sql-connector | Unblocks every other owner H 1 |
| `contracts/schemas.py` from VF schema | Tero | Pydantic | Every parallel branch reads from here |
| BookingAgent supervisor (mock sub-agents OK) + public-reachable deploy (Render/Fly/ngrok) | Tero | **FastAPI + Databricks Foundation Model APIs (`mlflow.deployments`)** | Orchestration core; without it nothing connects. Public deploy needed because Vercel React cannot SSE from `localhost`. |
| TriageAgent | Mian | **Python + Databricks FM APIs (Llama 3.3 70B)** + in-memory corpus | First stage; symptom → specialty |
| **TrustScorer v1 — single-model 4-factor** | Mian | **Python + Databricks FM APIs (Llama 3.3 70B)** | Base trust score; two-model upgrade in Layer 2 |
| RouterAgent | Tero | **Python + pandas/SQL over Delta** | Ranks candidates; Genie Code is Layer 4 stretch |
| Atomic Booking — single-row INSERT into `atomic_bookings` (4 struct columns) after parallel HTTP pre-validation | Tero | **Python + databricks-sql-connector + Delta single-row atomicity** | The operational killer; 4-tile flip reads the 4 struct columns of the just-written row |
| DLT pipeline Bronze→Silver→Gold (real) | Mian | **Lakeflow / DLT — Databricks-native, kept** | Grand Prize anchor; live-shown in pitch |
| Frontend: **Patient flow only** (input + map + 3 cards + reserve button) | Arushi | **React (Vite/Next) on Vercel + Leaflet** | The hero surface; doctor copilot is Layer 3 |
| Web Speech API voice input | Arushi | Browser native | 15-min add; required for "Hindi voice" demo line |
| Reasoning Panel **skeleton** consuming mock SSE | Arushi | React EventSource | Reserves UI real estate; real SSE in Layer 2 |

**Layer 1 demo state @ H 7:** type or speak Hindi symptom → 3 hospitals on map with mock trust scores → tap reserve → 4 tiles flip green. Reasoning panel shows pre-canned tokens. **No real verification yet — but the loop works end-to-end.**

### LAYER 2 — Улучшения базы (rubric anchors light up)

These take the base from "it works" to "it deserves prizes." Hard checkpoint at H 13.

| Component | Owner | Stack | What it earns |
|---|---|---|---|
| **Two-model TrustScorer** (Extractor Llama 3.3 70B + Validator Claude Opus 4.7, both Databricks-hosted, disjoint retrieval slices) | Mian | Python + Databricks Foundation Model APIs via `mlflow.deployments` | F1's verification depth; rubric 30% IDP + 35% Discovery; "all inference inside lakehouse" governance signal |
| **Per-field CI on each Trust factor** | Mian | Python + numpy | Brief Areas of Research explicitly asks for prediction intervals |
| **Click-to-source MLflow trace** wired to Trust factor cards | Mian | MLflow as logger; React modal renders trace JSON | Direct rubric hit (10% transparency); the F1 click moment |
| **Validator demotion visible** (1 hospital flagged "no anesthesiologist" → demoted) | Mian | Trust card flag UI in React | Pitch moment; **must be in demo script** |
| **Reasoning Panel real SSE** consuming live tokens from BookingAgent | Tero + Arushi | FastAPI SSE + React EventSource | F2's killer visualisation; the "judges watch AI think" moment |
| **Tier-1/Tier-2 routing logic** in BookingAgent | Tero | Python branching | Operational depth pitch ("two-tier coverage works day one") |
| **IntakeAgent for 2-3 fake Tier-1 hospitals** (mock signature OK) | Mian | FastAPI mock servers | Tier-1 demo with green "Verified Live" pulse |
| **Synthetic Live Stream** (±2 beds / 5 min) | Tero | Python cron + Delta append + WebSocket broadcast | Fills Tier-2 visual quietness; pitch tick lands mid-demo |
| **Outcome Loop UI playback** (no real cron/Twilio — only animation replay) | Tero | React animation + Python local timer | Closer line "first incentive system"; schema in Delta is enough |
| **NGO Desert Dashboard tab** (separate page, PIN-by-PIN gap filtering) | Arushi | React + REST → Delta aggregation | 25% Social Impact rubric anchor |
| **Dead Zone overlay** as toggle on hero map | Arushi | React + Leaflet GeoJSON layer | Same data on hero — judges see problem and solution simultaneously |
| **Confidence + last_verified_at on cards** | Arushi | React UI | Technical-honesty signal for ML judges |
| **Validator rule pack — 3 rules only** (no_anesthesiologist, no_ventilators, no_night_staff) | Mian | Python rule functions | Enough for demo demotion; more rules in Layer 3 |
| **Pre-compute Gold on 100-200 hospitals** (not full 10k) | Mian | Python batch job → Delta write | TrustScorer two-model latency manageable; Gold is frozen at demo |

**Layer 2 demo state @ H 13:** full Verify-4 → Book-4 working end-to-end. Reasoning panel streams real tokens. Validator demotes Hospital C visibly. Click-to-source opens MLflow trace with highlighted source sentence + counter-evidence. Synthetic stream tick visible on map. Outcome loop animation replays. NGO + Dead Zone toggle works.

⚠ **HARD CHECKPOINT @ H 13.** If Layer 2 not green: **freeze everything below**. Polish Layer 1+2 only. The 70%-vs-100% rule from F2 fires here.

### LAYER 3 — Wow (only if Layer 2 green @ H 13)

These are the "reach for the prize" features. Each can be **replaced with a pre-rendered animation or slide** if not built — pitch survives.

| Component | Owner | Stack | Replacement if not built |
|---|---|---|---|
| **Agent Reputation Score live aggregation** | Tero | Delta SQL aggregation | Pre-rendered card-stack animation: "Hospital A 0.95 → Hospital B 0.62" |
| **Counterfactual Replay opener** as slide-only (NOT engine) | Tero | Slide only (Keynote/Figma) | One slide: "38 lives changed in 90 days, simulated from research/01" — the engine itself is too expensive to build |
| **Doctor Transfer Copilot tab** (entire second surface) | Mian + Arushi | React tab + FastAPI endpoint | One screenshot in pitch deck: "next view, doctor-side transfer copilot" |
| **FHIR snippet generation** | Mian | Python `fhir.resources` or hardcoded JSON | Faked JSON with "FHIR-compatible" caption |
| **Genie Code live multi-step query** | Tero | Databricks Genie Code (Trial-available) | Pre-recorded screen capture with "captured live" caption |
| **MLflow Registry + lineage view** | Mian | MLflow REST | Static screenshot in slide |
| **BedPredictor real MLflow Registry serving** | Mian | MLflow + sklearn | Local serialized sklearn function; no Registry |
| **Validator rule pack — full 10+ rules** | Mian | Python rule functions | 3 rules from Layer 2 are enough |
| **IntakeAgent UC-signed identity** (real signing) | Mian | Unity Catalog identity API | Mock signature string |
| **Two-model pre-compute on full 10k** | Mian | Python batch + parallel SDK calls | 100-200 hospitals from Layer 2 |
| **Vector Search citation retrieval** | Mian | Mosaic AI Vector Search | Local FAISS index built from Gold |

**Layer 3 demo state @ H 16:** any subset of these landing makes the demo feel "complete." None of them are required for a passing demo.

### LAYER 4 — Stretch (only if all of Layer 3 green @ H 16)

These exist for the team to keep busy if everything above is genuinely shipped. **Default = NOT BUILT.**

| Component | Owner | Stack | Why stretch |
|---|---|---|---|
| Voice MCP Mode B (Fish Audio + OpenAI Realtime + outbound calls) | Tero | Python Fish SDK + OpenAI Realtime API | 6h cost; Web Speech (Layer 1) covers the "Hindi voice" demo line |
| Bridge Doctor Mode (D2D shared screen) | Mian | React + WebRTC | Third surface; Doctor Copilot tab from Layer 3 already too much |
| Ambulance moving animation on map | Arushi | React + Leaflet animated marker | Wow visual; eats frontend time |
| Real Twilio Media Streams | Tero | Twilio | Out of scope already |
| Real outcome scheduled job + Twilio/SMS ping | Tero | Python cron + Twilio SDK | UI playback from Layer 2 is enough for pitch |
| Genie Code live demo query | Tero | Databricks Genie Code | Public Preview behaviour on the trial 50-DBU/h warehouse is unpredictable; pandas RouterAgent (Layer 1) is the dependable path |
| Mosaic AI Vector Search | Mian | Databricks-native (Trial: 1 endpoint, Delta-sync) | Local FAISS in Layer 3 covers semantic retrieval; Vector Search only if storage-optimized index lands in our region |
| Foundation Model Fine-tuning (LoRA on Llama-3.2 etc.) | — | Mosaic AI Model Training | **Not in scope** — region-locked Public Preview, trial inclusion unverified, no labeled data, frontier LLMs already cover extraction |
| **Mosaic AI Agent Framework — thin-wrapper registration** | Tero | `databricks.agents` register over existing FastAPI BookingAgent | **Nice-to-have for perception, not capability.** Brief names "Agent Bricks for Foundation Model Training and Serving" in primary tech stack; registering our existing supervisor in Databricks Agent Framework adds the "we're using their flagship product" pitch line + native MLflow tracing + UC governance. Implementation stays Python+FastAPI underneath — no rewrite. **Build only if H 16 + everything else green.** Cost ~1-2h. Pitch line: *"Agent logic registered in Databricks Agent Framework with Unity Catalog governance; underlying implementation uses OpenAI/Anthropic SDKs for two-model independence."* |
| **Knowledge Assistant for Triage corpus** | Mian | Databricks Knowledge Assistant over symptom→specialty docs | Same logic — replaces in-memory corpus with native Knowledge Assistant if Layer 4 has time. Requires non-zero serverless budget policy + Production monitoring (Beta) — both Trial-available but require config. Cost ~2h. |

---

## 8.6 MVP Iteration Plan — 3 MVPs, 3 People, Parallel Folders

The 4-Layer view (Section 8.5) tells you **what is cuttable**. The MVP view tells you **where you can stop and still have a working demo**.

**The rule: every MVP is a strict superset of the previous one.** MVP N includes everything from MVP N-1, plus one new capability dimension. If catastrophic time pressure hits, the team falls back to the last completed MVP — not to a half-built next-MVP.

```
MVP 0 ─ Setup            (H 0-2)   ───── not demo-able; foundation
MVP 1 ─ Working Loop     (H 2-7)   ───── demo-able product #1 (5 hours)
MVP 2 ─ + Atomic + Two-Model
        + Reasoning Panel (H 7-13) ─── demo-able product #2 (6 hours, rubric-pass)
MVP 3 ─ + Tier-1/2 + Stream
        + Outcome + NGO + polish (H 13-19) ─── demo-able product #3 (6 hours, final)
```

Each MVP is **~5-6 hours of parallel work for 3 people**, with non-overlapping folders. Total: 3 demoable products, last one at H 19.

### ⚠ Timeline reality check

**Hour budgets in this section are aggressive estimates assuming zero blockers.** Independent estimation by review pass: realistic execution lands at **1.3–1.5× these numbers** (so MVP 2's 6h is really 8–9h on the wall clock). Plan accordingly:

- **Treat H 13 as the real cutoff for "everything must work end-to-end".** Not H 11, not H 14. If you hit H 11 and MVP 2 isn't 70% done, start cutting MVP 3 features now — don't wait for the hard checkpoint.
- **Each MVP has a "minimum viable cut" defined below** — the absolute reduced scope that still ships a demo-able artefact at the boundary. If wall-clock slip shows up, drop to the cut version, not the full version.
- **MVP 3 is Tier-2 and stretch — not the rubric pass.** MVP 2 is the rubric pass. If MVP 2 is shaky, MVP 3 work is wasted.

#### Per-MVP minimum viable cut

| MVP | Full scope | **Minimum viable cut (if behind at MVP boundary)** |
|---|---|---|
| **MVP 0** | All edition gates + contracts + mocks + demo flow + FastAPI deploy | **Stub gold table + `contracts/schemas.py` + Vercel URL live** — everything else can defer to start of MVP 1 |
| **MVP 1** | Voice + 3 cards + Triage + single-LLM TrustScorer + DLT 100 hospitals + Reasoning Panel skeleton + Reserve confirm | **Text input + 3 cards + Triage + scalar trust score + Reserve returns `{confirmed: true}`** — no DLT (read stub gold), no voice (type text), no Reasoning Panel skeleton (Layer 2 anchor instead) |
| **MVP 2** | Atomic 4-way + two-model TrustScorer + click-to-source + real SSE + Validator demotion + 3 rules | **Atomic single-row INSERT + Validator demotion on Hospital C + click-to-source on ONE factor + real SSE on ONE agent (extractor)** — drop two-model to single-model with hardcoded validator contradiction for Hospital C; drop 2 of 3 rules |
| **MVP 3** | Tier-1/2 routing + IntakeAgent mocks + Synthetic Stream + Outcome Loop + Reputation + NGO + Dead Zone + 3 rehearsals | **Synthetic Stream tick + Dead Zone overlay + 1 rehearsal** — drop IntakeAgent mocks (all hospitals fall through to Tier 2), drop Outcome Loop (one slide), drop Reputation (one slide), drop NGO tab (Dead Zone overlay alone covers Social Impact rubric) |

**Pre-warm rule:** If you're cutting features at the MVP boundary, **announce the cut at the standup** so other owners stop waiting on the cut feature's contract. Silent cuts cause idle-wait by other owners.

---

### MVP 0 — Setup (H 0-2, 2 hours)

**Not demo-able.** Foundation. Tools provisioned, demo flow locked, contracts published.

**Tero (~2h, owns `tero/` and `contracts/` and `docs/`):**
- [ ] Databricks **Trial for Work** workspace + perms for 3 owners. Confirm region is `us-east-1` or `us-west-2` (preserves Foundation Model Fine-tuning Public Preview, even though we're not using it — keeps options open).
- [ ] **Edition validation gates** (run all and post results in `docs/edition-status.md`, see `research/09-databricks-editions.md` for the full list):
  - [ ] **Foundation Model APIs catalog (PRIMARY)**: `mlflow.deployments.get_deploy_client("databricks").list_endpoints()` must return both `databricks-meta-llama-3-3-70b-instruct` and `databricks-claude-opus-4-7` (or equivalent Claude endpoint) → unblocks two-model TrustScorer
  - [ ] Outbound network (secondary, only if FM APIs miss a model we need): `requests.get("https://api.openai.com/v1/models")` and `https://api.anthropic.com/v1/models` → fallback path only
  - [ ] Vector Search: create a test `storage-optimized` Delta-sync index → confirms 1-endpoint Trial allowance
  - [ ] DLT pipeline: scaffold runs end-to-end with one bronze/silver step
  - [ ] Apps: deploy a hello-world Databricks App, confirm URL — used only as backup if Vercel deploy breaks
  - [ ] Lakehouse Monitoring: open the Quality tab on a UC table, confirm "Create monitor" is enabled → only matters for the optional drift-slide screenshot
- [ ] Download `VF_Hackathon_Dataset_India_Large.xlsx` → extract VF pydantic schema → commit `contracts/schemas.py`
- [ ] Commit `mocks/*_output.json` for every cross-folder contract — Mian and Arushi build against these in MVP 1
- [ ] **LOCK demo flow** in `docs/demo-script.md` — second-by-second flow, never deviates after this point
- [ ] FastAPI repo skeleton in `tero/supervisor/`, hello-world `mlflow.deployments.predict()` call against `databricks-meta-llama-3-3-70b-instruct`
- [ ] **Pick public-reachable FastAPI deploy target** (Render / Fly.io / Railway / ngrok tunnel) and commit deploy config — Vercel-hosted React cannot consume SSE from `localhost`. **Owner: Tero. No-go blocker for MVP 1 SSE.**

**Mian (~2h, owns `mian/`):**
- [ ] Sniff sample of `VF_Hackathon_Dataset_India_Large.xlsx` — confirm schema with Tero
- [ ] **STUB gold table** in Delta: 50 hardcoded hospitals committed within first hour. **Critical unblocker** — Tero and Arushi cannot start MVP 1 until this lands.
- [ ] DLT pipeline scaffold in `mian/dlt-pipeline/` (Bronze stage only)
- [ ] Hello-world extraction prototype in `mian/trust-scorer/` — single field, single hospital, via `mlflow.deployments.predict(endpoint="databricks-meta-llama-3-3-70b-instruct", ...)`

**Arushi (~2h, owns `arushi/`):**
- [ ] React project bootstrapped in `arushi/app/` (Vite + Leaflet + Tailwind or shadcn)
- [ ] Vercel deploy connected — confirm one URL works
- [ ] EventSource consumer hello-world in `arushi/reasoning-panel/` — connects to Tero's FastAPI hello-world

**MVP 0 acceptance:** Tero + Mian + Arushi each push one commit, Vercel URL is live, contracts are in git. **All three start MVP 1 from green.**

---

### MVP 1 — "Working Loop" (H 2-7, 5 hours)

> *"Speak Hindi symptoms → 3 hospitals appear with mock trust scores → reserve confirms."*

The simplest working product, end-to-end, fully demo-able. **No real verification yet, no atomic transaction yet, no real reasoning panel yet — but the user loop is closed and the demo runs.**

**What this MVP includes:**
- Patient flow UI working — text + Hindi voice input → 3 hospital cards on map → reserve confirms
- TriageAgent calls Databricks-hosted Llama 3.3 70B via `mlflow.deployments`, returns specialty + urgency
- TrustScorer single-LLM v1 — 4-factor extraction with one Llama 3.3 70B call per facility (via `mlflow.deployments`)
- BookingAgent FastAPI orchestrates: Triage → TrustScorer → simple SQL ranking → 3 cards
- Reasoning Panel skeleton — consumes mock SSE with canned tokens
- DLT pipeline running on 100 hospitals
- "Reserve" button shows simple confirmation modal

#### Tero (~5h)

Folders: `tero/supervisor/`, `tero/router/`

- [ ] **`tero/supervisor/`** — FastAPI `BookingAgent` service: `/recommend` POST endpoint, function-call orchestration via Databricks FM APIs (`mlflow.deployments` client), calls TriageAgent + TrustScorer + RouterAgent in sequence
- [ ] **`tero/supervisor/sse.py`** — mock SSE endpoint streaming canned reasoning tokens (Arushi consumes this)
- [ ] **`tero/router/`** — pandas/SQL ranking module: reads Gold via `databricks-sql-connector`, ranks by trust × distance × specialty match, returns top 3
- [ ] **`tero/supervisor/reserve.py`** — simple POST `/reserve` returns `{confirmed: true, eta: 23}` (no Delta transaction yet — that's MVP 2)
- [ ] Commit one E2E smoke test: `pytest tero/supervisor/test_e2e.py` calls `/recommend` with sample input, asserts 3 hospitals returned

#### Mian (~5h)

Folders: `mian/dlt-pipeline/`, `mian/triage/`, `mian/trust-scorer/`

- [ ] **`mian/dlt-pipeline/`** — Lakeflow/DLT real: Bronze→Silver→Gold for 100 hospitals (replaces stub from MVP 0). Silver tier handles geocoding + dedup + language detection.
- [ ] **`mian/triage/`** — Python module + Databricks FM API function calling (`mlflow.deployments` against `databricks-meta-llama-3-3-70b-instruct`): `triage(symptoms_text, language)` → `{specialty, urgency, confidence}`. In-memory symptom→specialty corpus loaded from JSON.
- [ ] **`mian/trust-scorer/v1_single_model.py`** — single Llama 3.3 70B call per facility via `mlflow.deployments`, 4-factor extraction (bed/oxygen/drug/specialist), returns scalar trust + per-factor scalars (no CI yet, no Validator yet)
- [ ] Commit `mocks/trust_scorer_output.json` so Tero and Arushi can render against real shape
- [ ] Verify TrustScorer reads from Gold via `databricks-sql-connector`

#### Arushi (~4h)

Folders: `arushi/app/`, `arushi/reasoning-panel/`, `arushi/voice-input/`

- [ ] **`arushi/app/`** — React Patient flow page: text chat input, map (Leaflet, Maharashtra/UP focus), 3 hospital cards rendered from `/recommend` response
- [ ] **`arushi/voice-input/`** — Web Speech API integration: mic button, Hindi recognition, transcript fills chat input
- [ ] **`arushi/reasoning-panel/`** — React component consuming Tero's SSE endpoint, renders agent-tagged tokens (`🩺`, `🔍`, `🗺`) as they stream
- [ ] **`arushi/app/components/HospitalCard.tsx`** — card with name, distance, 4-factor trust badges, Reserve button
- [ ] Reserve button POSTs to `/reserve` and shows confirmation modal
- [ ] Vercel deploy passes manual smoke test

#### MVP 1 acceptance criteria

- [ ] User opens Vercel URL → speaks Hindi symptom → 3 hospital cards appear on map within 5 seconds
- [ ] Reasoning Panel shows canned tokens streaming during the call
- [ ] Reserve button shows confirmation modal
- [ ] No manual intervention needed for full demo run
- [ ] All 3 owners can pull main and run end-to-end locally

#### Demo story (45 sec)

*"Speak Hindi symptoms — 'पिताजी को सीने में दर्द' — and AarogyaNet pulls from 100 verified hospitals across the Databricks lakehouse. The agents reason in real time on the side panel. Three ranked recommendations appear on the map with trust scores. This is the foundation — and we built more on top of it."*

**Stop here if:** catastrophic. You still have a healthcare-finder demo that judges can use.

---

### MVP 2 — "Atomic + Two-Model + Reasoning + Click-to-Source" (H 7-13, 6 hours)

> *"...and watch the agents really think. Validator catches a contradiction (Hospital C — no anesthesiologist). Click any score to see the source sentence. Tap Reserve — four reservations commit atomically, all green tiles. Demo theatre fully wired."*

The biggest single MVP — combines **operational killer (atomic booking)** + **rubric anchors (two-model verification + click-to-source)** + **demo killer (real reasoning panel)** all in one push. **This is the rubric-pass MVP.**

**What this MVP adds (on top of MVP 1):**
- **Atomic 4-way Delta transaction** with rollback (Tero) + 4-tile flip animation (Arushi)
- **Two-model TrustScorer** — Extractor (Databricks-hosted Llama 3.3 70B) + Validator (Databricks-hosted Claude Opus 4.7), disjoint retrieval slices, per-field CI (Mian)
- **Validator demotion visible** — Hospital C demoted in real time (Mian + Arushi)
- **Click-to-source** — clicking a Trust factor opens modal with source sentence + counter-evidence (Mian + Arushi)
- **Real SSE wiring** — BookingAgent streams real agent tokens (Tero + Arushi)
- **Validator rule pack** — 3 rules: `no_anesthesiologist`, `no_ventilators`, `no_night_staff` (Mian)

#### Tero (~6h)

Folders: `tero/transfer/`, `tero/supervisor/` (extends from MVP 1)

- [ ] **`tero/transfer/atomic.py`** — `book_atomic(hospital_id, factors_required)`: (1) parallel async HTTP pre-validation probes against 4 mock endpoints (bed/ambulance/doctor/drug), (2) if all 4 pass → single-row INSERT into `main.healthcare.atomic_bookings` with bed/ambulance/doctor/drug as struct columns, (3) if any pre-validation fails → return `{atomic_txn_id: null, rollback_reason}` without writing. **No multi-statement Delta tx — single-row write IS the atomic unit at the SQL connector layer.**
- [ ] **`tero/transfer/mock_endpoints.py`** — 4 fake side-effect endpoints (ports 9101 bed / 9102 ambulance / 9103 doctor-Tier-2 / 9104 drug) returning configurable success/failure. Hospital A's drug endpoint seeded `409 stockout` for the demo failure-and-retry beat.
- [ ] **Schema migration:** Mian creates `main.healthcare.atomic_bookings` table with struct columns: `bed_reservation: STRUCT<reservation_id STRING, ward STRING, eta_min INT>`, `ambulance_dispatch: STRUCT<dispatch_id STRING, eta_min INT>`, `doctor_slot: STRUCT<slot_id STRING, doctor_name STRING>`, `drug_reservation: STRUCT<lock_id STRING, sku STRING>`. Owner: Mian, blocks Tero's `atomic.py`. **MVP 2 hour 7 deliverable.**
- [ ] **`tero/supervisor/sse_real.py`** — replace mock SSE with real Databricks FM API streaming via `mlflow.deployments` (server-side stream relay); distinct event types `triage` / `extractor` / `validator` / `router` / `transfer` so frontend can color-code agents
- [ ] **`tero/supervisor/reserve.py`** — upgrade to call `book_atomic`, return real `atomic_txn_id` or `rollback_reason`
- [ ] Demo failure-and-retry script: family taps Reserve A → drug fails (mock endpoint configured to fail) → all 4 tiles flash red → auto-suggest B → commit → all 4 green

#### Mian (~6h)

Folders: `mian/trust-scorer/` (extends), `mian/validator-rules/` (new)

- [ ] **`mian/trust-scorer/v2_two_model.py`** — full two-model architecture (both models served by Databricks Foundation Model APIs via `mlflow.deployments` client):
  - Extractor: `databricks-meta-llama-3-3-70b-instruct` reading facility notes via local FAISS or Vector Search
  - Validator: `databricks-claude-opus-4-7` reading **rosters/equipment logs separately** — disjoint retrieval slice
  - Composer: combines `extractor_confidence × (1 - validator_contradiction) × evidence_completeness`, returns per-field `mean ± 95% CI`
  - No external API keys, no outbound whitelist dependency
- [ ] **`mian/validator-rules/rules.py`** — 3 Python rule functions: `no_anesthesiologist(roster)`, `no_ventilators(equipment)`, `no_night_staff(roster)` — return `{matched: bool, evidence_pointer, confidence}`
- [ ] **`mian/trust-scorer/precompute.py`** — Python batch script that runs two-model scoring on 100-200 hospitals **offline** → writes results back to Gold. Demo reads frozen Gold (latency-safe).
- [ ] **`mian/dlt-pipeline/silver_sentences.py`** — Silver-tier step: `nltk.sent_tokenize()` over each facility note, write `silver_facility_sentences` Delta table with `{sentence_id, hospital_id, paragraph_idx, sentence_idx, text}` rows. Sentence IDs flow into Extractor/Validator prompts as the citation alphabet. **Blocks click-to-source — must land before mlflow_trace.py.**
- [ ] **`mian/trust-scorer/mlflow_trace.py`** — every scoring call wrapped in `mlflow.start_run`; trace JSON includes the `citation_id` emitted by Extractor/Validator (looked up in `silver_facility_sentences` + `silver_rosters`). Expose REST endpoint `/trace/{trust_score_id}` returning `{citation_id, sentence_text, counter_row_id, counter_row_text}` — Arushi's modal renders, no client-side retrieval.
- [ ] Hospital C is hand-curated to demote: claims "Advanced Surgery 24/7" + roster has no anesthesiologist → contradiction conf 0.92

#### Arushi (~5h)

Folders: `arushi/app/` (extends), `arushi/reasoning-panel/` (extends), `arushi/click-to-source/` (new)

- [ ] **`arushi/app/components/AtomicBookingTiles.tsx`** — 4-tile component (bed/oxygen/drug/specialist) with flip animation: grey → green on commit, red flash → grey on rollback. Hooked to `/reserve` response.
- [ ] **`arushi/reasoning-panel/`** — switches from mock SSE to real EventSource at Tero's `/sse` endpoint. Color-codes agents (`triage` blue, `extractor` purple, `validator` red, `router` green, `transfer` orange).
- [ ] **`arushi/click-to-source/SourceModal.tsx`** — modal that opens when user clicks a Trust factor on a card. Calls `/trace/{id}` REST endpoint, renders MLflow trace JSON with **highlighted source sentence** in the original facility note + **highlighted counter-evidence row** in the staff roster.
- [ ] **`arushi/app/components/HospitalCard.tsx`** — extend with red "DEMOTED" badge for flagged hospitals + per-factor confidence interval display (`0.94 ± 0.03`)
- [ ] Cards now show `mean ± CI` per factor, click-able to open source modal

#### MVP 2 acceptance criteria

- [ ] All MVP 1 criteria still pass
- [ ] Hospital C visibly demoted with red "no anesthesiologist" badge
- [ ] Click any Trust factor → modal opens with source sentence highlighted + counter-evidence row
- [ ] Reserve A → 4 tiles attempt → drug fails → all flash red → rollback → auto-suggest B → 4 tiles green
- [ ] Reasoning Panel streams 5 distinct color-coded agent token types
- [ ] Each factor shows `mean ± CI` instead of single number

#### Demo story (90 sec)

MVP 1 + *"...and look — Hospital C is demoted automatically. Our Validator runs Claude Opus 4.7, independent of the Extractor running Llama 3.3 70B — both served from Databricks Foundation Model APIs, reading different slices of the data, so their errors are largely uncorrelated. Validator found 'Advanced Surgery 24/7' claimed but no anesthesiologist on the roster. Contradiction confidence 0.92. Click any factor — see the exact source sentence. [Tap Reserve] Four sub-systems pre-validated in parallel, then a single Delta row commits with all four reservations as struct columns — atomic by Delta semantics. Drug stockout on Hospital A — no commit, no half-booking. Auto-suggest Hospital B — single-row INSERT, all four tiles green. Verification with row-level citations and atomic operational semantics."*

**Stop here if:** H 13 hard checkpoint, integration not green for MVP 3. **This is the rubric-pass demo.** Polish from here.

⚠ **HARD CHECKPOINT @ H 13** — *the* checkpoint of the hackathon.

---

### MVP 3 — "Tier-1/2 + Stream + Outcome + NGO + Polish" (H 13-19, 6 hours)

> *"...partners verified live (Tier 1 green pulse). Others on synthetic stream — and there it is, bed count just dropped. 2 hours later we ping the patient, retro-correct trust, drop reputation. NGOs use the same data — Bihar dialysis desert, 4 districts, zero facilities."*

Operational depth + social impact + final polish. **All four rubric pillars hit hard.**

**What this MVP adds:**
- **Tier-1/Tier-2 routing** in BookingAgent (Tero)
- **IntakeAgent FastAPI mock servers** for 2-3 fake Tier-1 hospitals + green "Verified Live" pulse (Mian + Arushi)
- **Synthetic Live Stream** ±2 beds / 5 min — pin shifts color visibly during pitch (Tero + Arushi)
- **Outcome Loop UI playback** — animation replays "T+2h ping → retro-correction → reputation tick" (Tero + Arushi)
- **NGO Desert Dashboard tab** + **Dead Zone overlay** on hero map (Mian + Arushi)
- **Counterfactual opener slide** + 3 demo rehearsals + submission package (everyone)

#### Tero (~6h)

Folders: `tero/sim-stream/` (new), `tero/outcome-loop/` (new), `tero/reputation/` (new), `tero/integration/` (new)

- [ ] **`tero/sim-stream/`** — Python script (cron OR Databricks scheduled job) that picks 30 random Tier-2 rows in Gold, applies `bed_count += randint(-2, +2)`, occasional `icu_full=True`, appends to Delta. WebSocket broadcasts to React for live pin re-color. **Time the demo tick to land mid-pitch.**
- [ ] **`tero/outcome-loop/`** — Python module that simulates a T+2h ping (no real Twilio), appends to `outcome_feedback` Delta table, retro-corrects Trust factor via SQL UPDATE on Gold. Animation contract for Arushi's playback.
- [ ] **`tero/reputation/`** — Delta SQL aggregation: `honest / total handshakes` per hospital. Pre-rendered React data passed to Arushi for animated card stack.
- [ ] **`tero/supervisor/tier_routing.py`** — Tier-1 (HAS-AGENT) → call IntakeAgent endpoint; Tier-2 (NO-AGENT) → BedPredictor + Synthetic Stream + voice fallback (Mode B is Layer 4 stretch, not in scope)
- [ ] **`tero/integration/`** — E2E pytest that walks: voice → 3 cards → Validator demotion → Reserve → atomic → outcome ping → reputation tick → NGO dashboard
- [ ] **Counterfactual opener slide** in `docs/pitch-deck/`: *"38 lives changed in 90 days, simulated from research/01"*
- [ ] **3 demo rehearsals at H 17, H 18, H 19** with the team — fix any timing/audio issues

#### Mian (~5h)

Folders: `mian/intake-agent/` (new), `mian/dead-zones/` (new), `mian/predictor/` (new)

- [ ] **`mian/intake-agent/server.py`** — FastAPI mock server template + 3 instances on ports 9201/9202/9203 with mock signature header. Each instance answers `bed?`, `oxygen?`, `drug?`, `specialist?` queries with hand-curated yes/no responses. Hospital A returns 4-yes (will pulse green); Hospital D returns 1-no (Validator demotion supplement).
- [ ] **`mian/dead-zones/aggregate.py`** — Python aggregation over Gold: group by PIN × specialty, count facilities with `trust ≥ 0.6`, return JSON shape `{pin: {specialty: {count, min_trust, nearest_km}}}` via REST endpoint `/dead-zones`
- [ ] **`mian/predictor/`** — Python sklearn forecaster (history-only) serialized with joblib, loaded by Tero's BookingAgent for Tier-2 bed predictions. MLflow as logger only.
- [ ] Hand-curate 2-3 hospitals as Tier-1 partners in stub gold table (Hospital A, B as fake-onboarded)
- [ ] **(if time):** Validator rule pack expanded from 3 → 6 rules

#### Arushi (~5h)

Folders: `arushi/ngo-dashboard/` (new), `arushi/dead-zone-overlay/` (new), `arushi/animations/` (new), `arushi/submission/` (new)

- [ ] **`arushi/ngo-dashboard/`** — React tab in main app: India PIN map (Leaflet GeoJSON), filter dropdown (specialty + min trust threshold), click PIN → "0 dialysis within 80km, population 4.2M" detail card. Calls `/dead-zones` REST endpoint.
- [ ] **`arushi/dead-zone-overlay/`** — toggle button on hero map that overlays the same Dead Zone GeoJSON as a red heatmap. One-tap on/off.
- [ ] **`arushi/animations/GreenPulse.tsx`** — Tier-1 hospital cards get a green "Verified Live" pulse animation when IntakeAgent handshake returns 4-yes
- [ ] **`arushi/animations/OutcomePing.tsx`** — replay animation: clock advances to T+2h → SMS bubble appears → trust factor visibly drops → reputation card-stack ticks one notch
- [ ] **`arushi/animations/StreamTick.tsx`** — pin color shift animation triggered by WebSocket message from Tero's Synthetic Stream
- [ ] **`arushi/submission/`** — README, demo video (rehearsal recording), Devpost writeup, GitHub polish, architecture diagram screenshot
- [ ] Pre-recorded fallback videos for every "live" moment: voice / reasoning / atomic / stream tick / NGO toggle

#### MVP 3 acceptance criteria

- [ ] All MVP 2 criteria still pass
- [ ] Hospital A shows green "Verified Live" pulse (Tier-1 IntakeAgent handshake)
- [ ] Synthetic Stream tick lands during pitch — at least one pin visibly shifts color
- [ ] Outcome Loop animation plays on demand — pings, drops, ticks
- [ ] NGO Dashboard tab loads PIN map, dialysis layer toggles to red over Bihar
- [ ] Dead Zone overlay toggles on hero map (one-tap red)
- [ ] Submission package complete in GitHub
- [ ] Backup demo recording exists for every live moment
- [ ] 3 full rehearsals complete without team intervention

#### Demo story (final, 150 sec)

MVP 2 + *"...and notice — Hospital A is Tier 1: it runs our IntakeAgent and gives us a signed real-time handshake. Green pulse means verified live. Hospital B is Tier 2 — no agent yet, but a synthetic stream keeps it fresh. [Stream tick fires] And there it is — bed count just dropped. Two hours later, we ping the patient. They say the drug arrived 30 minutes late. Trust drops, hospital reputation drops. First incentive system for honest healthcare data in India. And NGOs use the same Trust map — Bihar dialysis desert, 4 districts, zero facilities, here is your gap."*

**This is the actual finish line at H 19.**

---

### Total work distribution

| Owner | MVP 0 | MVP 1 | MVP 2 | MVP 3 | Total | New folders |
|---|---|---|---|---|---|---|
| **Tero** | 2h | 5h | 6h | 6h | **19h** | `tero/supervisor/`, `tero/transfer/`, `tero/router/`, `tero/sim-stream/`, `tero/outcome-loop/`, `tero/reputation/`, `tero/integration/` |
| **Mian** | 2h | 5h | 6h | 5h | **18h** | `mian/dlt-pipeline/`, `mian/triage/`, `mian/trust-scorer/`, `mian/validator-rules/`, `mian/intake-agent/`, `mian/dead-zones/`, `mian/predictor/` |
| **Arushi** | 2h | 4h | 5h | 5h | **16h** | `arushi/app/`, `arushi/voice-input/`, `arushi/reasoning-panel/`, `arushi/click-to-source/`, `arushi/ngo-dashboard/`, `arushi/dead-zone-overlay/`, `arushi/animations/`, `arushi/submission/` |

Folder boundaries are strict — no owner edits another's folder. All cross-folder integration goes through `contracts/schemas.py` (Tero owns) and `mocks/*_output.json` (each owner commits a sample for their endpoint).

---

## 9. Build Order — At-A-Glance Timeline

The hour-by-hour task lists live in **Section 8.6 (MVP Iteration Plan)**. This section is the timeline summary + checkpoint discipline.

```
H 0   ──┐
        │ MVP 0 — Setup (2h)        ─── Tero locks demo + contracts;
H 2   ──┤                                Mian stubs gold table;
        │                                Arushi bootstraps React+Vercel
        │
        │ MVP 1 — Working Loop (5h) ─── Tero: BookingAgent + Router + mock SSE
        │                                Mian: DLT + TriageAgent + TrustScorer v1
H 7   ──┤                                Arushi: Patient flow + voice + panel skel
        │ ✓ Demo-able: speak symptom → 3 cards → reserve confirms
        │
        │ MVP 2 — Atomic + Two-Model + Reasoning + Click-to-Source (6h)
        │     Tero: Atomic 4-way Delta + real SSE
        │     Mian: Extractor⇄Validator + per-field CI + rule pack
H 13  ──┤     Arushi: 4-tile flip + click-to-source modal + real SSE consumer
        │ ⚠ HARD CHECKPOINT — if not green, FREEZE here
        │ ✓ Rubric-pass demo
        │
        │ MVP 3 — Tier-1/2 + Stream + Outcome + NGO + Polish (6h)
        │     Tero: sim-stream + outcome loop + reputation + Counterfactual slide
        │     Mian: IntakeAgent mocks (3 ports) + Dead Zone aggregation
H 19  ──┘     Arushi: NGO tab + Dead Zone overlay + animations + submission
            ✓ Final form demo
```

### Checkpoint discipline

**At H 7 (MVP 1 boundary):**
- 15-min standup. Each owner shows their folder running locally.
- If MVP 1 not green → **freeze MVP 2 start**, debug. Do not proceed before MVP 1 is demo-able.
- Demo flow document re-read by all 3 — confirm we're still building to it.

**At H 11 (informal MVP 2 health check):**
- 5-min sync. Each owner answers: "If we stopped now, what's not working in MVP 2?"
- If 3+ items not working → **switch to MVP 2 minimum viable cut now** (drop two-model, drop click-to-source for 3 of 4 factors, drop 2 of 3 rules). Don't wait for the H 13 hard checkpoint to find out you're behind.
- Pre-warm Foundation Model API endpoints (a 5-min cold-start spike at demo time kills the panel).

**At H 13 (MVP 2 boundary — THE HARD CHECKPOINT):**
- 30-min standup with full demo run-through.
- If MVP 2 green → proceed to MVP 3.
- If MVP 2 NOT green → **stop everything**. Use H 13-19 to polish MVP 1+2 only, pre-record fallbacks, rehearse pitch. MVP 3 is then never started. Last-completed MVP is your demo. **This is The One Rule firing.**

**At H 19 (final):**
- 3 full demo rehearsals (one with each fallback drill: synthetic stream manual, IntakeAgent mocked, Reasoning Panel cached tokens)
- Submission package complete in GitHub
- Backup demo recording for every "live" moment

### Cross-MVP rules (apply throughout)

- **Never edit another owner's folder.** Open a PR or commit a contract example in `contracts/` or `mocks/` instead.
- **All "live" demo moments need pre-recorded fallback** by H 18.
- **Demo flow document never deviates** from the H 0-2 lock.
- **Daily integration green** — every MVP boundary requires `pytest tero/integration/` to pass on main before next MVP starts.

---

## 10. Demo Theatre Discipline

**Two layered rules** combine here:

1. **[T] Rule (revised under stack split):** on every second of the demo, something **agentic** must be moving on screen — Reasoning Panel tokens, 4-tile flip, click-to-source modal, synthetic-stream pin shift, Reputation tick. *"Databricks-native"* now means "data lineage from Delta + atomic Delta transaction visibly committed" — not "a Databricks-hosted dashboard tab is open."
2. **[F2] Rule:** the Live Agent Reasoning Panel must be visibly streaming during every second of live segments. Stale panel = wasted demo seconds.

For each killer firing, this checklist must be satisfied:
- [ ] BookingAgent trace ID visible in dev panel
- [ ] **[F2] Reasoning Panel streaming agent tokens** — not just final outputs
- [ ] MLflow 3 trace events live-streaming with row-level citations
- [ ] **[F1] Click-to-source works on every Trust factor card** — opens MLflow trace, highlights exact sentence
- [ ] Genie Code chat renders multi-step output (Phase 3)
- [ ] When IntakeAgent handshake fires, Trust badge animates "Verified Live" green pulse
- [ ] **[F2] Synthetic Stream tick lands during pitch** — at least one pin shifts color visibly
- [ ] When Outcome Loop fires, Reputation Score visibly ticks down/up
- [ ] When Atomic Booking commits, all 4 reservation tiles flip from grey → green simultaneously; on rollback, all 4 flash red and reset
- [ ] **[F2] Dead Zone overlay toggle works on hero map** — Maharashtra rural goes red instantly
- [ ] Lakehouse Monitoring drift bars (slide screenshot) flashed in pitch deck — **not** opened as live Databricks tab during demo per stack split
- [ ] Vector Search top-k visible somewhere on screen (citation source) — sourced from Trial endpoint OR local FAISS, identical UX

**Hierarchy of "if only one thing works" priorities:**
1. Reasoning Panel streaming (lose this, lose F2's killer)
2. Atomic Booking 4-tile flip (lose this, lose T's killer)
3. Click-to-source MLflow trace (lose this, lose F1's killer + transparency rubric)
4. Synthetic Stream tick (lose this, demo loses the "live" feel for Tier 2)
5. Voice input via Web Speech (lose this, type Hindi from clipboard)

---

## 11. Demo Script (second-by-second, ~2:30 full / ~1:25 MVP-2-only)

The merge extends Tero's 2-minute script with Friend 2's 4-beat pitch structure and Reasoning Panel discipline.

**Two scripts live here.** Default is the full 2:30 script (assumes MVP 3 ships). If H 13 hard checkpoint fires "freeze, don't start MVP 3", switch to the **MVP-2-only short script** at the bottom of this section — same opener, drops Tier 1 pulse / Synthetic Stream / Outcome Loop / NGO tab beats. Whoever delivers the demo memorises both.

**00:00-00:15 — [T] Counterfactual Replay opener**
Slide: *"In the last 90 days of this dataset, 1,247 emergency admissions. Replayed through our system: 38 lives changed."* Statistic from research/01.

**00:15-00:25 — [F2 Beat 1: real statistic + Beat 2: human problem]**
Slide: *"India: 0.5 hospital beds per 1,000 in rural areas. WHO recommends 2.5. Families don't just suffer from lack of healthcare — they suffer from lack of information."*

**00:25-00:50 — [Hero] Patient flow opens (Vercel URL — React app)**
- [F2] Click mic. Speak Hindi: «बुखार और सीने में दर्द, पटना»
- [F2] Reasoning Panel streams Triage → TrustScorer (Extractor + Validator) → Router
- 3 hospitals render with 4-factor Trust + intervals + verification source
- **[F2] silence the narration here — let judges watch the AI think (Beat 3)**

**00:50-01:10 — [F1] Validator demotion moment + click-to-source**
- Hospital C visibly demoted: "Advanced Surgery: 0.18 — Validator contradiction 0.92 (no Anesthesiologist on roster)"
- [F1] **Click the flagged factor** → MLflow trace panel slides in
- [F1] Original facility note highlighted: *"Advanced Surgery available 24/7"*
- [F1] Roster row 44 highlighted: *"Dr. Sharma 9-5 only, no on-call anesthesiologist"*

**01:10-01:25 — [F2] Synthetic Stream tick (timed for this moment)**
- A green pin shifts to yellow on the Patna map
- *"And there it is — bed count just dropped at Hospital X. The system knows immediately."*
- *"In production this is IVR. In our demo we simulate to show the architecture."* [F2 honesty line]

**01:25-01:45 — [T] Atomic Booking commit moment**
- Family taps Reserve A
- 4-tile animation: bed/oxygen/drug/specialist flip green simultaneously
- Confirmation: ETA 23 min, Dr. Sharma waiting
- **[F2] secondary buttons appear:** [Call 108] [Ola] [Uber]

**01:45-02:00 — [T] Doctor Transfer Copilot tab — [Layer 3, slide if not built]**
- Switch to tab. Sending hospital → 3 receivers ranked by Trust × Reputation
- FHIR + PDF generated. Ambulance ETA countdown
- **Map shows ambulance moving** — [Layer 4 stretch — pre-recorded GIF if not built]
- *Fallback if Layer 3 cut at H 13:* one screenshot in pitch deck — "next view, doctor-side transfer copilot" — then jump straight to 02:10 NGO beat

**02:00-02:10 — [T] Genie Code chat — [Layer 4 stretch — pre-recorded fallback by default]**
- Judge prompt: *"Rural Bihar appendectomy with part-time doctors."*
- Multi-step agent: extract → score → return with citations
- Reasoning Panel streams during query
- *Default playback is pre-recorded screen capture with caption "captured live" — live Genie Code is only attempted if H 16 + everything else green*

**02:10-02:20 — [F1+F2] NGO/Dead Zone reveal — [Dead Zone overlay = Layer 2; NGO tab = Layer 2; Reputation tick = Layer 3]**
- Toggle Dead Zone overlay on hero map: rural Maharashtra goes red — [Layer 2, must work]
- Switch to NGO Dashboard tab: dialysis layer shows Bihar gaps — [Layer 2, must work]
- [T] Drift slide flashed (Lakehouse Monitoring screenshot, not a live tab switch)
- Reputation Score ticks for one hospital — visible in React UI — [Layer 3, slide-replaceable]

**02:20-02:30 — [F2 Beat 4 + T closer]**
- *"AarogyaNet doesn't just build a map. It builds an intelligence network that gets smarter every time a family searches, every time a hospital updates."*
- *"Trust verified across 4 dimensions. Booked atomically as a single Delta row. Honesty incentivized. First incentive system for honest healthcare data in India. All inference inside the Databricks lakehouse — Llama Extractor and Claude Validator served by Foundation Model APIs."*

---

### MVP-2-only short script (~1:25, fires if H 13 hard checkpoint freezes MVP 3)

Use this if Tier-1 IntakeAgent pulse, Synthetic Stream tick, Outcome Loop, Reputation, and NGO tab were not built. Dead Zone overlay is Layer 2 so still in.

**00:00-00:15** — Counterfactual opener slide (same as full script)
**00:15-00:25** — F2 Beat 1 + Beat 2 statistic + human story (same as full script)
**00:25-00:50** — Hero patient flow opens, Hindi voice, Reasoning Panel streams Triage → Extractor → Validator → Router, 3 cards render (same as full script)
**00:50-01:10** — Validator demotion + click-to-source (same as full script)
**01:10-01:25** — Atomic Booking commit moment: Reserve A → drug stockout 409 → all 4 tiles flash red → auto-suggest B → single-row Delta INSERT → all 4 green
**Skip:** Synthetic Stream tick (MVP 3), Doctor Transfer Copilot tab (Layer 3), Genie Code chat (Layer 4), NGO tab (MVP 3)
**01:25** — Toggle Dead Zone overlay on hero map (rural Maharashtra goes red) → closer line: *"Trust verified across 4 dimensions. Booked atomically. All inference inside the Databricks lakehouse. Dead zones visible the same moment we route around them. This is the rubric pass — the rest is operational depth we kept off the demo to land what matters."*

Closer is shorter, more honest, and survives any MVP-3 cut.

---

## 12. Fallback Strategy

| Failure | Swap to | Setup before demo | Source |
|---|---|---|---|
| Reasoning Panel streams stop mid-demo | Cached token playback (replay last good run) | H 18 record cached run | F2 |
| Synthetic Stream stops ticking | Manual "force tick" button in dev panel | H 16 wire button | F2 |
| Hindi voice fails on browser | Pre-typed Hindi in clipboard | H 18 prepare clipboard | F2 |
| Voice MCP realtime API unavailable (if Mode B built) | `VOICE_MODE=mock` (env var flip) — pre-recorded audio | Pre-record H 16-18 | T |
| IntakeAgent handshakes fail | All hospitals routed as Tier 2 (Predictor + Synthetic Stream + voice) | Verified to fall back gracefully | T |
| Genie Code query times out | Pre-recorded screen capture + slide overlay "captured live" | Record H 16-18 | T |
| Vercel deploy down | Run React app on `localhost:5173` and present from there; back-up Databricks App URL ready as second fallback | Keep `npm run dev` warm H 16-18 | T (post-merge) |
| External LLM APIs (`api.openai.com` / `api.anthropic.com`) blocked by Trial whitelist | **No-op for primary path** — TrustScorer + Triage + BookingAgent already run on Databricks Foundation Model APIs (Llama + Claude, both hosted by Databricks). External SDKs are only used if a specific model isn't in the FM API catalog. | Validation gate H 0: confirm both `databricks-meta-llama-3-3-70b-instruct` and `databricks-claude-opus-4-7` endpoints exist | merge |
| BookingAgent crashes mid-demo | Mock SupervisorResponse JSON file → frontend reads from local | Have file on disk H 16-18 | T |
| MLflow lineage panel slow / click-to-source slow | Static screenshot of trace panel in slide | Screenshot H 16-18 | T+F1 |
| Atomic Booking transaction fails on stage | Backup video of successful run | Record H 16-18 | T |
| Outcome Loop simulation slow | Pre-rendered timeline video | Render H 16-18 | T |
| Validator misfires (false contradiction at demo) | Hand-curate 3 demo hospitals known to behave | Curate H 14-15 | F1 |
| TrustScorer two-model latency too high | Pre-compute Gold offline; demo reads frozen Gold | Pre-compute H 13 | F1 |
| Dead Zone overlay slow on full geo data | Pre-aggregate into static GeoJSON | Pre-aggregate H 15 | F1 |

**Rule (combined from T + F2):** every "live" demo moment must have a pre-recorded version that's been tested. No moment is "either live or nothing." **And:** every "live" demo moment must be paired with reasoning-panel cached playback so the panel never goes stale.

---

## 13. Risks & Open Questions

| Risk | Severity | Mitigation | Source |
|---|---|---|---|
| Brief names Genie Code; Trial provides it but Public Preview behaviour on the trial 50-DBU/h warehouse is unpredictable | Medium | pandas RouterAgent is the primary path (Layer 1); Genie Code is Layer 4 stretch with pre-recorded fallback | T |
| SSE from FastAPI on Vercel-hosted React works only if FastAPI is reachable from the user browser (not behind a Databricks-only network) | High | FastAPI service is hosted **outside** Databricks (e.g. Render, Fly.io, Railway, or local tunnel via ngrok during demo); never inside Databricks Apps | merge |
| Databricks Foundation Model APIs missing one of our chosen endpoints (Llama 3.3 70B or Claude Opus 4.7) on Trial | Medium | H 0 validation gate runs `mlflow.deployments.list_endpoints()` first. Fallback path: pick the closest-available FM API endpoint (e.g. `databricks-meta-llama-3-1-405b-instruct` or any Claude variant). Last-resort fallback only: switch one of the two models to external `api.openai.com`/`api.anthropic.com` (provided outbound is whitelisted). Two-model independence preserved either way. | merge |
| Trial expires day 14, assets deleted 60 days later if no payment method added | Medium | Mirror notebooks (.dbc), MLflow runs, Delta exports, App URLs and demo videos to GitHub before day 14. `tero/` owns this backup checklist. | merge |
| $400 trial credit ceiling | Low (we're not running tight) | Atomic Booking + DLT + pre-compute Gold on 100-200 hospitals all comfortable; no GPU compute. Friend's fine-tune idea stays parked. | merge |
| Two-model TrustScorer latency: Llama + Claude (both Databricks-hosted) per row × 10k rows is expensive | High | Pre-compute offline H 0-7 on 100-200 hospitals; demo reads frozen Gold table; full 10k stays in research/01 numbers | F1 |
| Reasoning Panel only impresses if first tokens arrive < 200ms | High | Use Foundation Model APIs streaming via `mlflow.deployments` (server-side) + SSE relay through FastAPI; pre-warm endpoints H 16; cached fallback for demo query | F2 |
| IntakeAgent installation impossible at real hospitals in 24h | Medium | Fake 2-3 hospitals as Tier 1 partners for the demo; honest about the rest being Tier 2 | T |
| Synthetic Stream feels "fake" if pitched poorly | Medium | F2 honesty line: *"In production: IVR. In demo: simulate to show architecture."* | F2 |
| Outcome loop has no real outcomes in 24h | Medium | Time-warp simulation: replay historical "outcomes" against synthetic routings | T |
| BookingAgent + IntakeAgents are both Python services (no Mosaic AI Supervisor) — coordination is plain HTTP | Low | This is by design; supervisor logic is FastAPI routing + Databricks FM API function calling via `mlflow.deployments` | T (resolved by stack split) |
| Atomic 4-way Delta transaction has limited demo impact if not visualized | High | Tile-flip animation must be wired before Phase 2 ends (Arushi + Tero) | T |
| Counterfactual Replay needs historical mortality data | Medium | Synthesize from research/01 + research/04 stats; label as "reconstructed" | T |
| **Mian's load is the highest in the team** — owns DLT pipeline + TriageAgent + two-model TrustScorer + IntakeAgent + Dead Zone aggregation | **Critical** | Stub Validator as no-op H 1, ship single-model TrustScorer in MVP 1 (H 0-7) before two-model split in MVP 2 (H 7-13). Tero pairs on Delta plumbing where bandwidth allows. | merge |
| Tero's load — BookingAgent + Atomic + SSE + Outcome + Reputation + Sim Stream + Router | High | Voice MCP Mode B is **dropped to Phase 3 stretch** to free hours | merge |
| Arushi's load — Reasoning Panel + Hero map + 2 tabs + Dead Zone overlay + voice input | High | Reasoning panel reuses chat-message component; tabs reuse layout shell | merge |
| 10k records source format unknown — Mian's DLT depends on it | High | Mian H 0-1 sniff sample; **stub gold table H 1 unblocks team regardless** | T |
| Hindi voice on Web Speech API may misfire on chest-pain edge cases | Medium | Mian vets Hindi prompts H 14; clipboard fallback for demo | F2 |
| Two-model errors might still correlate if retrieval slices overlap | Medium | F1 discipline: Extractor sees notes, Validator sees rosters/equipment — disjoint slices, enforce in retrieval config | F1 |
| Click-to-source MLflow trace UI new for the team | Medium | Mian owns; Pre-build sample trace H 7 to validate UX flow | F1 |
| Reasoning Panel + Atomic Booking + Genie Code all on demo screen — visual overload | Medium | Hero map full-bleed; reasoning panel collapsible side; Atomic Booking is modal | merge |

---

## 14. Out of Scope

**Hard out of scope (never built):**
- Real ABDM API integration (mock only — production requires CERT-IN audit, see research/02)
- Real 108 dispatch (mock only; deeplink only)
- HMIS integration (out — covered in research/03 as known dead-end)
- Multi-language beyond Hindi/English for Phase 2 (Bhojpuri/Marathi/Tamil/Bengali deferred)
- Mobile-native apps (web-only React for hackathon)
- Production-grade auth (any local auth or Vercel auth is enough for demo)
- Long-term storage of voice recordings (delete after demo)
- Real hospital onboarding for Tier 1 (faked for 2-3 hospitals in demo)
- WhatsApp integration (not enough budget after merge — drop entirely)
- **Counterfactual Replay engine** (replaced with one slide in Layer 3 — never build the engine itself)
- **Databricks Apps + appkit SDK** — replaced by React on Vercel
- **Unity Catalog signed identities for IntakeAgent** — mock signature is enough

**Demoted to Layer 3 (Wow — slide-replaceable):**
- Doctor Transfer Copilot tab — one screenshot fallback
- FHIR snippet generation — faked JSON acceptable
- MLflow Registry + lineage view — static screenshot fallback
- BedPredictor with MLflow Registry + Models-from-Code — local serialized sklearn fallback
- Validator rule pack beyond 3 rules — Layer 2 has 3, more is Layer 3
- IntakeAgent UC-signed identity — mock signature fallback in Layer 2
- Two-model pre-compute on full 10k — Layer 2 stops at 100-200 hospitals
- Mosaic AI Vector Search — local FAISS fallback works just as well for demo

**Demoted to Layer 4 (Stretch — default NOT BUILT, nice-to-have only):**
- Voice MCP Mode B (Fish + OpenAI Realtime + outbound calls)
- Bridge Doctor Mode (D2D shared screen)
- Ambulance moving animation
- Real outcome scheduled job + Twilio/SMS ping (Layer 2 has UI playback only)
- Genie Code live multi-step query (Trial-available but Public Preview unpredictability; pandas RouterAgent is the primary path)
- **Mosaic AI Agent Framework — thin-wrapper registration** of our existing FastAPI BookingAgent. Adds the "we use Agent Bricks" pitch line + native MLflow tracing + UC governance. Underlying logic stays Python, no rewrite. ~1-2h cost. Build only if everything else green at H 16.
- **Mosaic AI Knowledge Assistant** for Triage corpus — replaces in-memory corpus only if Layer 4 has time. Requires non-zero serverless budget policy + Production monitoring (Beta) config.

The principle: **anything that can be replaced with a slide / animation / canned response without weakening the pitch is moved to Layer 3+.** This is the F2 rule applied to every component.

---

## 15. Success Criteria

**Demo-day pass:**
- Patient speaks Hindi via mic → 3 hospitals appear on map with 4-factor Trust scores
- **[F2] Reasoning Panel streams agent tokens during query — Triage, Extractor, Validator, Router visible**
- **[F1] One factor on one card is click-able → MLflow trace opens → exact source sentence highlighted in original note + roster row counter-evidence**
- One hospital shows Tier 1 "Verified Live" green pulse from IntakeAgent handshake
- **[F2] Synthetic Stream tick lands during pitch — at least one pin visibly shifts color**
- Validator demotes one hospital visibly (e.g., "Advanced Surgery without Anesthesiologist" — contradiction 0.92)
- Family taps Reserve → atomic 4-way booking commits with tile-flip animation
- Outcome Loop simulation shows Trust + Reputation update live for one hospital
- Doctor switches to Transfer Copilot tab → 3 receivers + FHIR packet + ambulance ETA
- **[F1] NGO Desert Dashboard tab** + **[F2] Dead Zone overlay** both functional
- Genie Code accepts at least one judge-typed query live (canned fallback ready)
- React app is reachable on a public Vercel URL (Databricks App URL kept as warm backup only — never the primary demo target)
- MLflow 3 Registry shows TrustScorer (two models) + Predictor versioned with row-level traces

**Pitch quality:**
- Counterfactual Replay opens with a real number (T)
- F2 Beat 1 statistic + Beat 2 human story land in first 30 seconds
- Demo segment has Reasoning Panel streaming and **no narration over agent thinking** (F2 Beat 3)
- Architecture diagram shows BookingAgent + 4 sub-agents + IntakeAgent + Reasoning Panel SSE
- Closer combines T's "First incentive system" + F2's "intelligence network"
- Demo screen never goes static; Databricks-native primitive always moving AND reasoning panel always streaming

**Rubric self-score target:**
- 35% Discovery & Verification — two-model TrustScorer + Validator + Outcome Loop + Reputation = full coverage (T+F1)
- 30% IDP Innovation — 4-factor extraction with two-model verification over 10k unstructured + click-to-source citations + LLM-in-DLT data cleaning (F1+F2)
- 25% Social Impact — NGO Desert Dashboard + Dead Zone overlay + Counterfactual Replay (F1+F2+T)
- 10% UX/Transparency — Reasoning Panel streaming + click-to-source on every Trust factor (F2+F1)

---

## 16. Provenance Attribution Table

The complete bill of materials. Every component shows where it came from and what conflict (if any) was resolved.

| Component | Provenance | Rationale | Conflict resolved |
|---|---|---|---|
| BookingAgent supervisor | T | Operational orchestration; no F1/F2 alternative | — |
| TriageAgent | T | F1 doesn't have it; F2's Triage is functionally equivalent | — |
| **TrustScorer (two-model inside)** | **H = T structure + F1 verification** | T's 4-factor structure with F1's Extractor⇄Validator architecture inside each factor | F1 separate Validator merged into TrustScorer for surface area |
| Validator (as separate agent) | F1 → merged into TrustScorer | F1's idea preserved; component count reduced | F1 standalone Validator dropped; behaviour kept |
| BedPredictor | T + F2 stream input | Tier-2 predictor consumes synthetic stream signal | — |
| RouterAgent (Genie Code) | T | Brief explicitly names Genie Code; F1/F2 use simpler queries | — |
| Atomic Booking | T | Visualisable demo killer; F2 alternative (deeplinks) kept as secondary | F2 deeplinks demoted to secondary buttons on card |
| Ola/Uber/108 deeplinks | F2 | Easy "I'll handle transport myself" path; secondary to atomic booking | (above) |
| IntakeAgent (Tier 1) | T | Two-tier coverage core; F1/F2 don't have peer concept | — |
| **Synthetic Live Stream** | **F2** | Patches T's Tier-2 visual quietness; cheap to build, high demo gain | F2 stream replaces T's "voice fires for Tier-2" as primary visual aliveness signal |
| Voice input — Web Speech API | F2 | 15-min add, primary voice path | F2 vs T Voice MCP — Web Speech wins as primary |
| Voice MCP Mode B (full stack) | T | Phase 3 stretch only; dropped from default scope | (above) |
| **Live Agent Reasoning Panel** | **F2** | Bridges all three plans visually; rubric-aligned for transparency | — |
| Outcome Learning Loop | T | Unique to Tero's spec; closer pitch line depends on it | — |
| Agent Reputation Score | T | Unique to Tero's spec; *"first incentive system"* line | — |
| **Click-to-source MLflow trace** | **F1** | Direct rubric hit (transparency 10% + IDP 30%); cheap to build on top of T's MLflow tracing | — |
| **Per-field trust with CI** | **F1** | Brief Areas of Research asks for prediction intervals | T had CI at facility level; F1's per-field CI replaces it |
| **Different models for Extractor vs Validator** | **F1** | Errors stop correlating; cheap rubric/pitch win | T used single-LLM extraction; F1's two-model wins |
| **`evidence_completeness` score** | **F1** | Captures data silence as signal | New addition not in T |
| NGO Desert Dashboard (tab) | F1 (extends T) | First-class NGO surface | T also has it; F1's PIN-by-PIN gap filtering is cleaner |
| Dead Zone overlay (hero map toggle) | F2 | Same data as NGO dashboard, on hero map | New addition; complements NGO tab |
| LLM function calls in DLT (Data Cleaning) | F2 | T's DLT was generic; F2's pattern adds inline LLM cleaning | — |
| Hero discipline (one main page, tabs) | F2 | Frontend dispersal risk → contained | T had 3 surfaces; F2's hero rule wins |
| **"DO NOT BUILD EVERYTHING" rule** | **F2** | Only spec with explicit scope discipline | Promoted to Section 0 — supersedes everything |
| Pitch 4-beat structure | F2 | Stat → human → demo (silent) → scale | T had unstructured pitch; F2's beats win |
| Counterfactual Replay opener | T | Quantitative hook before F2's beats | Combined with F2 Beat 1 statistic |
| Confidence + last_verified_at on cards | F2 | Technical-honesty signal | F1's per-field CI is on factors; F2's freshness is on card meta |
| Hour-by-hour build schedule | T | More detailed than F2's; mapped to hours not days | F2's "lock demo flow in H 0-2" rule injected |
| Phase 2 hard checkpoint (drop to "Cut if behind") | F2 | Discipline at H 13 | New — explicit in build order |
| **Stack split — Databricks for data layer only** | User decision (post-merge) | DLT pipeline + Delta atomic + optional Vector Search; everything else Python/React | T's Mosaic AI Agent Framework, Knowledge Assistant, Genie Code, Databricks Apps SDK all dropped from primary path |
| **MVP iteration plan (5 demoable products)** | User decision (post-merge) | Each MVP is shippable on its own; strict superset progression | Replaces Layer-only thinking; adds where-to-stop guidance |
| **React on Vercel as frontend deploy** | User decision (post-merge) | Replaces `*.databricksapps.com` URL | Decouples frontend from Databricks (esp. Trial outbound network constraints + 14-day expiry) |
| **Local FAISS as Vector Search fallback** | User decision (post-merge) | Mosaic AI Vector Search is optional, not required | Resilient against Trial 1-endpoint cap + region-locked storage-optimized index |
| **Trial for Work as primary edition** | User decision (post-merge) | 14-day Premium with $400 credits | Restores Vector Search, Lakehouse Monitoring, Genie Code, multi-App that Free Edition explicitly blocks; outbound network restriction still applies — see `research/09-databricks-editions.md` |

---

## 17. Comparison To Sibling Specs

| | **This (merge)** | Tero (multiagent-design) | Friend 1 (aarogya-trust) | Friend 2 (aarogyanet-react) |
|---|---|---|---|---|
| **Killer** | Verify-4 (two-model) → Atomic Book with reasoning visible + outcome closer | Verify-All-4 + Atomic Booking + Outcome Loop | Extractor⇄Validator → contradictions → trust with CI | Live reasoning panel + 3-agent ReAct + dead zones |
| **Posture** | Operational + verifiable + theatrical (with one rule discipline) | Operational | Analytical | Demo-first |
| **Agents** | 6 (Triage, two-model TrustScorer-with-Validator-inside, Router, IntakeAgent, TransferCoord, BookingAgent supervisor) | 8+ | 2 + 1 orchestrator | 3 in linear ReAct |
| **Live data** | Tier-1 IntakeAgent + Tier-2 Synthetic Stream + Outcome ping | IntakeAgent handshakes + outcome ping | None (batch) | Synthetic stream only |
| **Voice** | Web Speech API primary + Voice MCP Mode B as Phase 3 | Voice MCP only | None | Web Speech only |
| **Verification depth** | Two-model + per-field CI + click-to-source | Single LLM + Validator second-pass | Two-model + per-field CI + click-to-source | Confidence + last_verified_at |
| **NGO surface** | Tab + hero overlay | Separate tab | Separate tab | Hero overlay only |
| **Transport** | Atomic 4-way Delta + secondary deeplinks | Atomic 4-way Delta | None | Deeplinks only |
| **Scope risk** | Medium (One Rule contains it) | High | Low | Medium |
| **One Rule** | **Quoted in Section 0 — supersedes everything** | Implicit in fallback | Implicit | Explicit |

---

## 18. How To Use This Spec

If the team adopts the merge, **delete the three sibling specs** and treat this as the source of truth. If the team wants to compare paths during planning:

1. **Read sibling specs first** in order: Tero → Friend 1 → Friend 2 (operational → analytical → demo-first arc)
2. **Read this merge spec second**, in this section order:
   - **Stack Boundary** (right after One Rule) — what runs where
   - **Section 8.5 Priority Tiers** — what is base / wow / stretch
   - **Section 8.6 MVP Iteration Plan** — where you can stop and still demo
   - **Section 16 Provenance Table** — attribution + stack split decisions

3. **Lock the demo flow in H 0-2** per Section 9 + The One Rule

4. **Build MVP-by-MVP, not feature-by-feature.** Each MVP is a shippable product:
   - MVP 1 @ H 7 — minimal end-to-end loop (mock SSE, single-LLM trust, fake reserve)
   - MVP 2 @ H 10 — atomic booking + real reasoning panel SSE
   - MVP 3 @ H 13 — two-model + click-to-source (rubric-pass)
   - MVP 4 @ H 16 — Tier-1/2 + stream + outcome + NGO (full rubric)
   - MVP 5 @ H 19 — polish + counterfactual + rehearsal (final form)

5. **At MVP 3 hard checkpoint (H 13)**, if not green: freeze. Polish MVP 1+2+3 only, use H 13-19 for fallback recording and rehearsal. MVP 4+ then never started. Last completed MVP is your demo.

6. **Every Layer 3+ item has a fallback** (slide / animation / canned response) listed in Section 8.5.

7. **Stay inside the stack boundary during MVP 1-3.** Do not reach for Mosaic AI Agent Framework, Knowledge Assistant, Genie Code, or Databricks Apps SDK during the base build — those are Layer 4 stretch nice-to-haves added on H 16+ only if everything else green. Use Python + FastAPI + **Databricks Foundation Model APIs (via `mlflow.deployments`)** + React on Vercel for the core. External OpenAI/Anthropic SDKs are **fallback-only** (used if a specific FM API endpoint is missing on Trial — see Section 12). Wrap with Mosaic AI Agent Framework registration **at the end** for the "we use Agent Bricks" pitch line — never before.

**Quick reference — what to build first if everything fails:**
- The 5 things you absolutely cannot lose (in priority order):
  1. Reasoning Panel streaming via FastAPI SSE (lose → no F2 killer)
  2. Atomic Booking 4-tile flip on Delta (lose → no T killer)
  3. Click-to-source on at least one factor (lose → no F1 killer + transparency rubric tanks)
  4. Validator demotion visible on one hospital (lose → IDP rubric tanks)
  5. Synthetic Stream tick during pitch (lose → demo loses "live" feel for Tier 2)

If only those 5 work plus MVP 1 base (FastAPI BookingAgent + Python TriageAgent + single-model TrustScorer + Atomic Booking + React patient flow + Web Speech), the demo passes.

**Final reminder — the stack boundary again:**
> ✅ Databricks: ingest, clean, structure, Delta tables, optional embeddings
> ❌ Databricks: frontend, agent logic, fast prototyping

