# Mian — Your README

> Main spec: `../docs/superpowers/specs/2026-04-25-healthcare-multiagent-design.md`
> JSON contracts: `../contracts/`
> Deadline: **19 hours total** from work start (2026-04-25)
> Connections: Tero (Supervisor) calls your BedPredictor; Mubarak (Triage) feeds you specialty hint

## What you own

| Subfolder | Component | Stack | Phase |
|---|---|---|---|
| `dlt-pipeline/` | Lakeflow / DLT medallion pipeline: bronze → silver → gold | DLT, Delta, Python | 1 |
| `predictor/` | BedPredictor — UC function calling MLflow-served forecaster | Python, MLflow, sklearn, UC functions | 1→2 |

## What you build

Two related components:

1. **DLT pipeline:** ingest the 10k messy hospital records → clean Delta tables (bronze/silver/gold).
2. **BedPredictor:** classical ML model that predicts P(bed | hospital, time), registered in MLflow Model Registry under Unity Catalog.

**Why you:** your `Heart-Disease-Predictor`, `cancer_stage_prediction`, `handling-missing-values`, `Standardization-of-data` notebooks are exactly this shape — tabular ML preprocessing + classifier. Direct portfolio match.

## Schedule (19 hours total)

### H 0-1 — workspace access + sniff data (1h)
- [ ] Get Databricks workspace + Unity Catalog perms (Tero provisions)
- [ ] Tero hands you the 10k records source (CSV / JSON / scraped HTML — format TBD)
- [ ] Inspect schema: what columns exist, missing-value rates, dedup keys

### H 1-5 — Phase 1a: DLT pipeline (4h)
- [ ] Create `dlt-pipeline/` notebook
- [ ] **Bronze layer:** raw 10k records → Delta table, no cleaning
- [ ] **Silver layer:** normalize addresses (geocode lat/lon), dedupe by (name + city), map specialty taxonomy
- [ ] **Gold layer:** routing-ready — joined with district population, sample bed counts (synthetic if needed)
- [ ] DLT data quality rules: not-null on critical columns, drop-on-fail
- [ ] Smoke test: `gold` table has ≥9000 rows after dedup

### H 5-9 — Phase 1b: BedPredictor v1 (4h)
- [ ] Create `predictor/` Python package
- [ ] Generate synthetic historical bed-occupancy data (24h × 7d × 100 hospitals = 16800 rows)
- [ ] Train baseline: time-of-day + day-of-week + hospital → P(bed)
- [ ] Use sklearn (RandomForestRegressor or GradientBoostingRegressor)
- [ ] Save with **MLflow Models-from-Code** pattern (judges look for this — Care Cost Compass uses it)
- [ ] Register in MLflow Model Registry under Unity Catalog
- [ ] Wrap as UC function callable from Supervisor
- [ ] **Write `predictor/mock_output.json` immediately** — this unblocks Tero's Supervisor

### H 9-13 — Phase 2: feedback loop + monitoring (4h)
- [ ] Add Voice MCP feedback ingestion: when Voice MCP returns verified bed count, append to feature table
- [ ] Set up Lakehouse Monitoring on the predictor's inference table
- [ ] Drift dashboard: synthetic drift between Delhi vs Mumbai (judges love this)
- [ ] Confidence calibration: output `confidence` ∈ [0,1] alongside `p_bed`

### H 13-19 — Help + polish
- [ ] Help Mubarak: Hindi prompt content drafting (you speak Urdu, close enough phonetically)
- [ ] Help Tero: debug Supervisor → BedPredictor integration
- [ ] Demo theatre prep: MLflow lineage screenshot, Lakehouse Monitoring drift panel ready to click

## Output JSON contract

See `../contracts/predictor_output.py` (Pydantic) and `../contracts/predictor_output.json` (mock).

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

## Input you receive (from Supervisor)

```json
{
  "specialty": "cardiology",
  "city": "Lucknow",
  "timestamp": "2026-04-25T14:23:11Z",
  "candidate_hospital_ids": ["h_3421", "h_8821", "h_4412"]
}
```

## Dependencies

**Nothing blocks you in Phase 1.** You can build DLT + Predictor in parallel with everyone else.

**Tero is blocked by you** for the Predictor mock output (1-2h after you start). Drop `mock_output.json` ASAP.

## Risks

- 10k records source format unknown until day 0 — first hour spike to inspect.
- MLflow Models-from-Code is the right pattern (Care Cost Compass uses it). Use this approach over legacy model serialization.
- Pair with Mubarak: he doesn't have MLflow evidence; show him your first checkin.

## Smoke test

```bash
cd mian/predictor
pytest tests/smoke.py
```

Should pass: query `{specialty: "cardiology", city: "Lucknow"}` returns 3 hospital predictions matching contract.
