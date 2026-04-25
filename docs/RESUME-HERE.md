# RESUME HERE — quick context after /compact

> Read this first to pick up where Tero left off.

## Status snapshot (2026-04-25, last update mid-build)

**Edition:** Databricks Trial for Work, OAuth via `databricks auth login` (profile in `~/.databrickscfg`). Workspace `dbc-e60d2427-6951.cloud.databricks.com`, ID `7474647721046702`. SQL warehouse `a6cf21f5e91a2176` (Serverless Starter, RUNNING).

**Spec:** `docs/superpowers/specs/2026-04-25-healthcare-best-of-merge.md` — best-of merge of Tero/Friend1/Friend2 + Trial-aware corrections. Layer 1-3 = build, Layer 4 = nice-to-have (incl. Mosaic AI Agent Framework wrapper).

**Friend's alternate plan:** `/Users/terobyte/Downloads/implementation_plan.md` (AarogyaNet — Flask + rule-based, no LLM). User has not yet decided "ours / friend's / hybrid", but data layer below works for all three paths.

**Edition audit:** `research/09-databricks-editions.md` — Trial limits, GPU=no, outbound=restricted, Foundation Model APIs work intra-Databricks.

**Friend's data note:** Mubarak/Mian (same person?) cleaned data in his workspace; we loaded VF xlsx into ours, fully self-contained now.

## What is built (in Databricks)

```
workspace.default.
├── vf_hackathon_dataset_india_large    Bronze, 10000 rows, 41 cols
├── silver_facilities                    Cleaned + parsed JSON arrays + trust meta, 10000
├── gold_trust_rules                     Rule-based Trust on ALL 10000
├── gold_trust_llm                       LLM TrustScorer on 256 rich hospitals (Llama 3.3 70B)
├── gold_trust_final                     HYBRID (LLM where rich + rules elsewhere) — final source
└── gold_pin_capabilities                NGO Desert Map aggregation, 4964 PINs
```

Full numbers + decisions: see `docs/databricks-progress.md`.

## What works (verified)

- Foundation Model APIs available: Llama 3.3 70B (TESTED), Llama 4 Maverick, Llama 3.1 405B, GPT-5.x family, GPT OSS, Qwen3 80B, Gemma 3 12B, embeddings (BGE/GTE/Qwen3). **NO Claude** intra-Databricks.
- LLM TrustScorer pipeline: 256/262 successful, 0% parse errors, ~$0.30 cost.
- SQL queries via `python3 scripts/databricks/dbq.py "SELECT ..."`.
- Batch LLM via `python3 scripts/databricks/llm_trust.py` (parallelised, 10 workers).

## Demo anchors discovered

- **INHS Sanjivani (Kochi) — Trust 0.90 LLM-verified** (top hospital)
- **Bihar — 194 PINs zero oncology, 175 zero emergency**
- **Maharashtra — 1506 facilities but 611 PINs zero oncology** (density ≠ coverage)
- **256 LLM-verified vs 9744 rule-inferred** (two-tier badge story)

## Still TODO (data layer)

| Component | Status |
|---|---|
| Vector Search endpoint + index | Not started — Trial 1 endpoint, 1 VS unit, Delta-sync only |
| Atomic Booking 4 tables (bed/ambulance/doctor/drug) | Schema not designed yet |
| Outcome feedback append-only table | Schema only when needed |
| Agent Reputation view | Aggregation later |
| Second-model validation pass (Llama 4 Maverick on the 256) | Optional, would replace single-LLM with two-model |

## Open decisions for Tero

1. **Ours / friend's / hybrid?** User leaning hybrid — already implemented at data layer.
2. **Mubarak status** — was in original 4-person team.md, gone from current best-of-merge (3 people Tero/Mian/Arushi). Confirm with user.
3. **Vector Search creation** — Trial allows 1 endpoint; needs decision on what to index (facility descriptions + capabilities seems obvious).
4. **Whether to start writing app code** — user said "не пиши код" earlier, focused on Databricks first. Re-confirm before starting FastAPI/React.

## Quick resume actions

- Read `docs/databricks-progress.md` — full data layer status
- Read `docs/superpowers/specs/2026-04-25-healthcare-best-of-merge.md` — final spec
- Check `databricks current-user me` — confirm OAuth still valid
- `python3 scripts/databricks/dbq.py "SELECT trust_source, COUNT(*) FROM workspace.default.gold_trust_final GROUP BY trust_source"` — verify Hybrid Gold still there
