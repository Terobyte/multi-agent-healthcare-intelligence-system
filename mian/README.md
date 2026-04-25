# Mian — Your README

> Main spec: `../docs/superpowers/specs/2026-04-25-healthcare-best-of-merge.md`
> Pydantic contracts: `../contracts/schemas.py` (Tero commits in MVP 0)
> Deadline: **19 hours** from work start (2026-04-25)
> Team: **3 people** — Tero (orchestration + atomic + integration), you (full backend), Arushi (frontend)

## What changed vs. the previous spec

- **Mubarak is no longer on the team.** You absorb his old scope: TriageAgent, IntakeAgent (Tier-1 mocks), Hindi prompt content, Dead Zone aggregation. Your load is now the **broadest in the team — critical path.**
- **Stack boundary:** Databricks is data layer only. **No** Mosaic AI Agent Framework / Agent Bricks Supervisor / Knowledge Assistant. Your agents are plain Python modules calling Databricks Foundation Model APIs via `mlflow.deployments` client.
- **TrustScorer is now the rubric anchor and it's two-model.** Extractor (`databricks-meta-llama-3-3-70b-instruct`) reads facility notes; Validator (`databricks-claude-opus-4-7`) reads rosters/equipment **separately** (disjoint retrieval slices). Different model families = errors don't correlate. Both Databricks-hosted = no external API keys, no outbound whitelist risk → "all inference inside the lakehouse" governance pitch.
- **Per-field Confidence Intervals + click-to-source MLflow trace** are required (rubric 10% transparency + 30% IDP).
- **Validator is no longer a separate component** — subsumed into TrustScorer (same row, same time → reduces contract surface).
- **Vector Search is optional.** Local FAISS is the catastrophic fallback if Trial's storage-optimized index isn't enabled in your region.

## What you now own

7 subfolders. You are the backend + data + agent logic lead. Single point of failure for backend — mitigation is the strict MVP ladder below (single-model TrustScorer first, two-model second).

| Subfolder | Component | Stack | MVP |
|---|---|---|---|
| `dlt-pipeline/` | **Lakeflow / DLT** medallion: bronze → silver → gold. Silver does geocoding + dedup + specialty taxonomy + **inline LLM function calls for Data Cleaning** (this is where Databricks Model Serving earns its demo moment). | DLT, Delta, Python, FM API for cleaning | 0-1 |
| `triage/` | **TriageAgent** — symptom → specialty/urgency. `databricks-meta-llama-3-3-70b-instruct` via `mlflow.deployments`. In-memory symptom→specialty corpus from JSON/YAML. Vector Search is optional upgrade path. | Python, Databricks FM API, in-memory corpus | 1 |
| `trust-scorer/` | **Two-model TrustScorer** — Extractor (Llama 3.3 70B) reads notes, Validator (Claude Opus 4.7) reads rosters/equipment separately. Per-field `mean ± 95% CI` + extractor_confidence + validator_contradiction + citation. **The rubric anchor.** | Python, Databricks FM API (both models), MLflow as logger, FAISS or Vector Search | 1→2 |
| `validator-rules/` | 3 Python rule functions: `no_anesthesiologist`, `no_ventilators`, `no_night_staff`. Returns `{matched, evidence_pointer, confidence}`. More rules in Layer 3 only. | Python | 2 |
| `intake-agent/` | **IntakeAgent (Tier 1)** — FastAPI mock servers on ports 9201/9202/9203. Each answers `bed?` / `oxygen?` / `drug?` / `specialist?` with hand-curated yes/no. Mock signature header (UC-signed identity = Layer 3 stretch). Hospital A returns 4-yes (green pulse demo). | FastAPI mocks | 3 |
| `predictor/` | **BedPredictor (Tier 2 only)** — sklearn forecaster serialized with joblib, loaded by Tero's BookingAgent. MLflow as logger only. Hooked into Tero's synthetic stream as a live signal. | Python, sklearn, joblib, MLflow | 3 |
| `dead-zones/` | **Dead Zone aggregation** — Python aggregation over Gold: group by PIN × specialty, count facilities with `trust ≥ 0.6`, expose REST `/dead-zones`. Feeds Arushi's NGO Dashboard tab + Dead Zone overlay. | Python, Delta SQL, REST | 3 |

## MVP schedule (3 demoable products)

### MVP 0 — Setup (H 0-2, 2h)
- [ ] Sniff sample of `VF_Hackathon_Dataset_India_Large.xlsx` — confirm schema with Tero
- [ ] **STUB gold table** in Delta: 50 hardcoded hospitals committed within first hour. **Critical unblocker** — Tero and Arushi cannot start MVP 1 until this lands.
- [ ] DLT pipeline scaffold in `mian/dlt-pipeline/` (Bronze stage only)
- [ ] Hello-world FM API extraction prototype in `mian/trust-scorer/` — single field, single hospital, via `mlflow.deployments` client to confirm endpoints work

### MVP 1 — Working Loop (H 2-7, 5h) — demo-able #1
> *"Speak Hindi → 3 hospitals appear with mock trust scores → reserve confirms."*

- [ ] `mian/dlt-pipeline/` — real Lakeflow/DLT for **100 hospitals** (replaces stub from MVP 0). Silver tier: geocoding + dedup + language detection.
- [ ] `mian/triage/` — Python module + Databricks FM API (Llama 3.3 70B): `triage(symptoms_text, language)` → `{specialty, urgency, confidence, trace_id}`. In-memory corpus from JSON.
- [ ] `mian/trust-scorer/v1_single_model.py` — **single FM API call per facility**, 4-factor extraction (bed/oxygen/drug/specialist), returns scalar trust + per-factor scalars (no CI yet, no Validator yet)
- [ ] **Commit `mocks/trust_scorer_output.json`** so Tero/Arushi render against real shape
- [ ] Verify TrustScorer reads from Gold via `databricks-sql-connector`

### MVP 2 — Two-Model + Click-to-Source (H 7-13, 6h) — demo-able #2 (RUBRIC-PASS)
> *"...Validator catches Hospital C — no anesthesiologist. Click any score for source sentence."*

- [ ] `mian/trust-scorer/v2_two_model.py` — full two-model architecture, both via `mlflow.deployments`:
  - Extractor: `databricks-meta-llama-3-3-70b-instruct` reading **facility notes** via local FAISS or Vector Search
  - Validator: `databricks-claude-opus-4-7` reading **rosters/equipment logs separately** — disjoint retrieval slice (this is what makes errors uncorrelated)
  - Composer: `extractor_confidence × (1 - validator_contradiction) × evidence_completeness`, returns per-field `mean ± 95% CI`
- [ ] `mian/validator-rules/rules.py` — 3 functions: `no_anesthesiologist(roster)`, `no_ventilators(equipment)`, `no_night_staff(roster)` → `{matched, evidence_pointer, confidence}`
- [ ] `mian/trust-scorer/precompute.py` — Python batch script runs two-model scoring on **100-200 hospitals offline** → writes back to Gold. Demo reads frozen Gold (latency-safe — full 10k stays as research/01 numbers).
- [ ] `mian/trust-scorer/mlflow_trace.py` — every scoring call wrapped in `mlflow.start_run`; trace JSON includes source sentence indices. Expose REST endpoint `/trace/{trust_score_id}` so Arushi's modal fetches it for click-to-source.
- [ ] **Hand-curate Hospital C** to demote: claims "Advanced Surgery 24/7" + roster has no anesthesiologist → contradiction confidence 0.92. **Must be in demo script.**

⚠ **HARD CHECKPOINT @ H 13.** If MVP 2 not green — **freeze**, polish MVP 1+2 only, MVP 3 never starts. The One Rule fires here.

### MVP 3 — Tier-1 + Predictor + Dead Zones (H 13-19, 5h) — final
> *"...Tier-1 IntakeAgent gives signed handshake (green pulse). Tier-2 uses Predictor + stream. NGOs see Bihar dialysis desert, 4 districts, 0 facilities."*

- [ ] `mian/intake-agent/server.py` — FastAPI mock template + 3 instances on ports 9201/9202/9203 with mock signature header. Hand-curated responses:
  - Hospital A: 4-yes (will pulse green in Arushi's UI)
  - Hospital D: 1-no (Validator demotion supplement)
- [ ] `mian/dead-zones/aggregate.py` — aggregation over Gold, group by PIN × specialty, expose REST `/dead-zones` returning `{pin: {specialty: {count, min_trust, nearest_km}}}`
- [ ] `mian/predictor/` — Python sklearn forecaster (history-only, time-of-day + day-of-week + hospital → P(bed)) serialized with `joblib`, loaded by Tero's BookingAgent for Tier-2. **MLflow as logger only**, no Registry serving (that's Layer 3 stretch).
- [ ] Hand-curate 2-3 hospitals as Tier-1 partners in stub gold table (Hospital A, B as fake-onboarded)
- [ ] **(if time):** Validator rule pack expanded from 3 → 6 rules (Layer 3 stretch)
- [ ] Help Arushi: Hindi prompt phrasing for Web Speech edge cases (chest-pain phonetics)
- [ ] Help Tero: debug Supervisor → TrustScorer integration

## Output JSON contracts (you commit mocks first, real implementations later)

See `../contracts/schemas.py` (Pydantic, Tero commits in MVP 0) and your own `mocks/`.

```json
// trust_scorer_output.json (the rubric anchor)
{
  "hospital_id": "h_3421",
  "tier": 2,
  "factors": {
    "bed":        {"value": 0.94, "ci": 0.03, "verified_at": "2026-04-25T10:14Z", "source": "intake_agent",        "extractor_confidence": 0.96, "validator_contradiction": 0.0},
    "oxygen":     {"value": 0.98, "ci": 0.01, "verified_at": "2026-04-25T10:14Z", "source": "intake_agent",        "extractor_confidence": 0.99, "validator_contradiction": 0.0},
    "drug":       {"value": 0.91, "ci": 0.04, "citation":   "facility_note_p3_s4", "source": "extraction+validator","extractor_confidence": 0.94, "validator_contradiction": 0.05},
    "specialist": {"value": 0.18, "ci": 0.05, "citation":   "facility_note_p1_s2", "source": "extraction+validator","extractor_confidence": 0.88, "validator_contradiction": 0.92, "flag": "no_anesthesiologist"}
  },
  "trust": 0.16,
  "trust_ci": 0.06,
  "decay_per_hour": 0.04,
  "evidence_completeness": 0.85,
  "trace_id": "tr_xyz"
}

// triage_output.json
{ "specialty": "cardiology", "urgency": 3, "symptoms_parsed": [...], "confidence": 0.88, "trace_id": "tr_abc" }

// predictor_output.json
{ "predictions": [{"hospital_id": "h_3421", "p_bed": 0.72, "ci": 0.11, "age_min": 145}], "model_version": "v1", "trace_id": "tr_pred" }

// intake_handshake.json
{ "hospital_id": "h_A", "query": "bed?", "response": "yes", "signature": "mock_sig_xyz", "latency_ms": 84, "agent_version": "0.1" }

// dead_zones.json
{ "560001": {"dialysis": {"count": 0, "min_trust": null, "nearest_km": 87}, "trauma": {"count": 2, "min_trust": 0.41}} }
```

## Reference call shape (Databricks-hosted, no external SDK)

```python
import mlflow.deployments
from databricks import sql

client = mlflow.deployments.get_deploy_client("databricks")

# Extractor (Llama) — reads facility narratives
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

## Input you receive (from Tero's BookingAgent)

```json
{
  "specialty": "cardiology",
  "city": "Lucknow",
  "timestamp": "2026-04-25T14:23:11Z",
  "candidate_hospital_ids": ["h_3421", "h_8821", "h_4412"]
}
```

## Dependencies

- **You unblock everyone in MVP 0** by stubbing the gold table within H 1. Tero and Arushi can't start MVP 1 until that lands.
- **Tero waits on you** for `trust_scorer_output.json` mock (drop in `mocks/` ASAP in MVP 1) and the real two-model implementation in MVP 2.
- **Arushi waits on you** for click-to-source MLflow trace REST endpoint (`/trace/{id}`) by mid-MVP 2.
- You don't wait on anyone — you can build DLT + Triage + TrustScorer in parallel with everyone else.

## Stack constraints (important — changed)

- ✅ All LLM calls go through `mlflow.deployments.get_deploy_client("databricks")` — both models hosted by Databricks. **No external API keys**, no outbound whitelist risk. Pitch line: *"all inference runs on Databricks Model Serving, no PHI leaves the lakehouse."*
- ✅ Delta read/write via `databricks-sql-connector`. DLT pipeline is Databricks-native (kept — Grand Prize anchor, shown live in pitch).
- ✅ MLflow used as **logger only** (not as live demo theatre). Trace data is fetched via REST and rendered in Arushi's React UI for click-to-source.
- ✅ FAISS is fine as the local fallback for retrieval. Vector Search only if Trial's storage-optimized index lands in your region — same UX either way.
- ❌ **No** Mosaic AI Agent Framework / Knowledge Assistant / Agent Bricks Supervisor.
- ❌ **No** Lakehouse Monitoring as live demo (static screenshot in slide is OK).
- ❌ **No** Models-from-Code Registry serving in MVP 3 (sklearn + joblib is enough; Registry is Layer 3 stretch).

## Risks (yours specifically)

- **Your load is the highest in the team — critical path.** Mitigation: ship single-model TrustScorer in MVP 1 (H 2-7) before two-model split in MVP 2 (H 7-13). Tero pairs on Delta plumbing if bandwidth allows.
- **Two-model TrustScorer latency** (Llama + Claude per row × 100-200 rows) is expensive. Mitigation: pre-compute offline at MVP 2 boundary; demo reads frozen Gold.
- **Two-model errors might still correlate if retrieval slices overlap.** Discipline: Extractor sees notes, Validator sees rosters/equipment — strictly disjoint. Enforce in retrieval config.
- **Click-to-source MLflow trace UI is new for the team.** Pre-build a sample trace at H 7 to validate UX flow with Arushi.
- **VF dataset format is unknown until day 0** — first hour spike to inspect. Stub gold table by H 1 unblocks everyone regardless.
- **Validator misfires (false contradictions on demo)** would be embarrassing. Mitigation: hand-curate 3 demo hospitals known to behave (Hospital A clean, Hospital C contradictory, Hospital D borderline).

## Smoke test

```bash
cd mian/trust-scorer
pytest tests/smoke.py
```

Should pass: query for one hospital returns full `trust_scorer_output.json` shape with both `extractor_confidence` and `validator_contradiction` populated, factors with `mean ± ci`, and a `trace_id` resolvable through `/trace/{id}`.
