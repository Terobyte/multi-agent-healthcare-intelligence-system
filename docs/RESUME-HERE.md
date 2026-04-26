# RESUME HERE — quick context after /compact

> Read this first to pick up where Tero left off.

## Deploy status (2026-04-26 — updated)

**Backend (Railway):** `https://aarogyanet-api-production.up.railway.app`
**Frontend (Vercel):** `https://app-wine-pi.vercel.app` (project not git-connected — manual `vercel --prod`)
**Current deploy state:** 🟢 Backend GREEN — `/health` returns `{"status":"ok","fm_endpoints":20,"warehouse":"configured"}`.

> Note: earlier doc said "Render". That was wrong — actual host is Railway. `render.yaml` lingers in repo
> but is unused; the live `aarogyanet-api.onrender.com` URL returns 404 (`x-render-routing: no-server`)
> because no Render service is running.

### Smoke check
```bash
bash scripts/smoke_railway.sh
# Or:
curl -s https://aarogyanet-api-production.up.railway.app/health
```

### Auto-deploy
Railway listens to `main`. autoDeploy fires on every push to main.
Feature branches (e.g. `feat/sponsor-stack`) are NOT deployed until merged.

### Frontend wiring
`arushi/app/.env.production` carries `VITE_PUBLIC_URL=https://aarogyanet-api-production.up.railway.app`.
Without this baked in, Vite builds with `HAS_REAL_BACKEND=false` and the UI shows
"Backend unreachable — showing offline demo data" (correct degraded behavior).

### URL handoff
- **Mubarak** (`Mozzicato@users.noreply.github.com`)
- **Arushi** (`arushi2610@users.noreply.github.com`)

Message template:
> Hey! Our API is live at https://aarogyanet-api-production.up.railway.app — hit `/health` to confirm, `/docs` for the Swagger UI.

---

## Status snapshot (2026-04-25, last update mid-build)

**Edition:** Databricks Trial for Work, OAuth via `databricks auth login`.
**Workspace:** `dbc-17e9d40d-5056.cloud.databricks.com`, ID `7474645268518160`.
**Profile:** `tero2` (in `~/.databrickscfg`). Old `tero` profile points at expired/lost workspace `7474647721046702` — do not use.
**SQL warehouse:** `10fff96dd6d936b5` (Serverless Starter Small).
**Owner:** `jumabayevtemirlan@gmail.com` (Tero's primary Google account).

**Spec:** `docs/superpowers/specs/2026-04-25-healthcare-best-of-merge.md` — best-of merge of Tero/Friend1/Friend2 + Trial-aware corrections. Layer 1-3 = build, Layer 4 = nice-to-have (incl. Mosaic AI Agent Framework wrapper).

**Friend's alternate plan:** `/Users/terobyte/Downloads/implementation_plan.md` (AarogyaNet — Flask + rule-based, no LLM). User leaning hybrid — data layer below works for all three paths.

**Edition audit:** `research/09-databricks-editions.md` — Trial limits, GPU=no, outbound=restricted, Foundation Model APIs work intra-Databricks.

**Team identities** (from `team.md`, used for git commit attribution):
- Tero: default committer
- Danish "Mian": `MianDanish1122@users.noreply.github.com`
- Mubarak: `Mozzicato@users.noreply.github.com`
- Arushi: `arushi2610@users.noreply.github.com`

## What is built (in Databricks workspace.default.*)

```
├── vf_hackathon_dataset_india_large    Bronze, 10000 rows × 41 cols
├── silver_facilities                    Cleaned + parsed JSON arrays + trust meta, 10000
├── silver_facilities_text               Single doc_text col for embedding, 10000 (PK + CDF)
├── silver_facilities_text_idx           Vector Search Delta-sync index (BGE-large) — provisioning
├── gold_trust_rules                     Rule-based Trust + 4 factor proxies, 10000
├── gold_pin_capabilities                NGO Desert Map per PIN, 3736
├── gold_trust_llm                       Llama 3.3 70B Extractor scores, 256
├── gold_trust_llm_v2                    Llama 4 Maverick Validator scores, 255
├── gold_trust_two_model                 Joined v1+v2 with agreement metrics, 262
├── gold_trust_final                     HYBRID 4-tier badge (two-model / disagree / single / rule)
├── txn_atomic + 4 resource tables       Atomic Booking saga (bed/ambulance/doctor/drug)
├── outcome_feedback                     Append-only patient ping ledger
└── v_committed_bookings, v_agent_reputation, v_trust_calibrated  views
```

Reproducible via `scripts/databricks/00_bronze_ingest.py` → `01_silver.sql` → `02_gold_rules.sql` → `03_gold_desert.sql` → `04_gold_llm.py` → `04b_gold_llm_v2.py` → `05_gold_hybrid.sql` → `07_atomic_booking.sql` → `08_outcome_feedback.sql` → `09_demo_seed.sql` → `10_two_model_verify.sql` → `06_vector_search.py`.

## What works (verified)

- Foundation Model APIs available: GPT-5.x family, Llama 3.3 70B (TESTED), Llama 4 Maverick, embeddings (BGE/GTE). **NO Claude** intra-Databricks.
- LLM TrustScorer pipeline: 256/262 successful, 0% parse errors, ~$0.30 cost.
- LLM artifact preserved at `data/llm_artifacts/trust_results_llama_3_3_70b.jsonl` — survives any workspace loss.
- SQL queries via `python3 scripts/databricks/dbq.py "SELECT ..."`.
- Batch LLM via `python3 scripts/databricks/llm_trust.py` (parallelised, 10 workers).
- **`/triage` endpoint** — HTTP 200 locally (verified 2026-04-26). Keyword fallback + Llama 3.3 70B both working.
- **`gold_trust_final` (Mian's gold table)** — 10000 rows ✅ (rule-inferred=9738, two-model-verified=139, models-disagree=110, llm-verified=13). Block 16 RouterAgent gate is satisfied.
- **`v_trust_calibrated` view** — exists, 10000 rows ✅. Calibration arc demo (Aradhna 0.831→0.350) will work. No flag needed to Mian.

## Demo anchors (current workspace)

- **INHS Sanjivani (Kochi) — Trust 0.888, two-model-verified** (Llama 3.3 + Llama 4 Maverick agreed within 0.10 across 4 factors)
- **80 hospitals two-model-verified** / 169 models-disagree / 13 single-model / 9738 rule-inferred — 4-tier trust badge story
- **6 outcome pings on INHS Sanjivani** → reputation 1.0 → calibrated trust holds (working outcome learning loop demo)
- **Bihar — 149 PINs zero oncology, 130 zero emergency**
- **Maharashtra — 1492 facilities but 403 PINs zero oncology** (density ≠ coverage)
- **5 atomic bookings + 1 saga rollback** demo (txn_999 ambulance unavailable → all 4 resources released)

## Still TODO (data layer)

| Component | Status |
|---|---|
| Vector Search endpoint + index | Not started — Trial 1 endpoint, 1 VS unit, Delta-sync only |
| Atomic Booking 4 tables (bed/ambulance/doctor/drug) | Schema not designed yet |
| Outcome feedback append-only table | Schema only when needed |
| Agent Reputation view | Aggregation later |
| Second-model validation pass (Llama 4 Maverick on the 256) | Optional, would replace single-LLM with two-model |

## Quick resume actions

- `databricks current-user me -p tero2` — confirm OAuth still valid (re-auth via `databricks auth login --host https://dbc-17e9d40d-5056.cloud.databricks.com -p tero2`)
- `python3 scripts/databricks/dbq.py "SELECT trust_source, COUNT(*) FROM workspace.default.gold_trust_final GROUP BY trust_source"` — verify Hybrid Gold still there (expect 256 + 9744)
- Read `docs/databricks-progress.md` — full data layer status
- Read `docs/superpowers/specs/2026-04-25-healthcare-best-of-merge.md` — final spec
