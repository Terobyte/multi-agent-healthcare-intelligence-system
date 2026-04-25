# RESUME HERE — quick context after /compact

> Read this first to pick up where Tero left off.

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
├── gold_trust_rules                     Rule-based Trust on ALL 10000 + 4 factor proxies
├── gold_trust_llm                       LLM TrustScorer on 256 hospitals (Llama 3.3 70B)
├── gold_trust_final                     HYBRID (LLM where rich + rules elsewhere) — final source
└── gold_pin_capabilities                NGO Desert Map aggregation, 3736 PINs
```

Reproducible from scratch via `scripts/databricks/00_bronze_ingest.py` → `01_silver.sql` → `02_gold_rules.sql` → `03_gold_desert.sql` → `04_gold_llm.py` → `05_gold_hybrid.sql`.

## What works (verified)

- Foundation Model APIs available: GPT-5.x family, Llama 3.3 70B (TESTED), Llama 4 Maverick, embeddings (BGE/GTE). **NO Claude** intra-Databricks.
- LLM TrustScorer pipeline: 256/262 successful, 0% parse errors, ~$0.30 cost.
- LLM artifact preserved at `data/llm_artifacts/trust_results_llama_3_3_70b.jsonl` — survives any workspace loss.
- SQL queries via `python3 scripts/databricks/dbq.py "SELECT ..."`.
- Batch LLM via `python3 scripts/databricks/llm_trust.py` (parallelised, 10 workers).

## Demo anchors (current workspace)

- **INHS Sanjivani (Kochi) — Trust 0.90 LLM-verified** (top hospital, preserved across rebuild)
- **Bihar — 149 PINs zero oncology, 130 zero emergency**
- **Maharashtra — 1492 facilities but 403 PINs zero oncology** (density ≠ coverage)
- **256 LLM-verified vs 9744 rule-inferred** (two-tier badge story)

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
