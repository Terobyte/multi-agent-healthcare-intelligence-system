# Databricks Progress Log

> Live status of data layer work.
> Current workspace: `dbc-17e9d40d-5056.cloud.databricks.com`, ID `7474645268518160`, profile `tero2`, SQL warehouse `10fff96dd6d936b5` (Serverless Starter Small).
> Old workspace `dbc-e60d2427-6951` / `7474647721046702` lost access on 2026-04-25 — full data layer rebuilt in new workspace via `scripts/databricks/00→05` sequence. Numbers below reflect new state.
> Auth: OAuth via `databricks auth login` (no PAT needed). Profile lives in `~/.databrickscfg`.

## ✓ Done

### 1. Edition validation (Trial for Work)
| Check | Result |
|---|---|
| Foundation Model APIs available | ✅ 20+ endpoints — `databricks-meta-llama-3-3-70b-instruct`, `databricks-gpt-5-5`, Llama 4 Maverick, Qwen3, Gemma, GPT-OSS, embeddings |
| Llama 3.3 70B chat invocation | ✅ Tested — RESPONSE: "OK" |
| GPT-5.x family | ⚠ Hit "PERMISSION_DENIED rate limit 0" on demo call (per-endpoint quota; need per-tier check) |
| **Claude on Trial?** | ❌ **NOT available** — only OpenAI GPT-5.x + Llama + Qwen + Gemma + GPT-OSS |
| Vector Search endpoints | ⚠ Empty (need to create one) |
| Cluster policies | ✅ Personal Compute available |
| SQL warehouse | ✅ "Serverless Starter" Small RUNNING — `10fff96dd6d936b5` (current workspace) |

**Spec impact:** F1's two-model verification can use **Llama 3.3 70B (Extractor) + GPT-5.5 (Validator)** OR **Llama 3.3 + Llama 4 Maverick** OR **Llama 3.3 + Qwen3 80B** for model-family independence. Claude path is dead intra-Databricks; would need external Anthropic API for it.

### 2. Bronze table — VF dataset loaded
- `workspace.default.vf_hackathon_dataset_india_large` — 10,000 rows × 41 cols
- Owner: `jumabayevtemirlan@gmail.com`
- Type: MANAGED Delta

### 3. Data profile (saved findings)

**Scale:**
- 10,000 facilities, 194 distinct states/regions
- Top facility types: clinic 6011, hospital 2789, dentist 740, doctor 276, pharmacy 184
- Top states: Maharashtra (1506), Uttar Pradesh (1058), Gujarat (838), Tamil Nadu (630), Kerala (597)

**Data quality (real null rates):**
| Field | % missing |
|---|---|
| numberDoctors | **93.7%** |
| capacity | **99.0%** |
| officialPhone | 13.5% |
| officialWebsite | 59.5% |
| yearEstablished | 92.1% |
| equipment | 84.0% |
| procedure | 66.0% |
| capability | 35.8% |
| affiliated_staff_presence | 57.1% |

**Trust meta-signals (VF schema already provides):**
- avg social media count: 2.06
- 42.9% have affiliated staff presence
- 26.0% have custom logo
- avg 5.6 facts about org
- avg 2,955 followers (when present)

**Critical finding for TrustScorer pre-compute target:**
- 2,789 hospitals total
- **262 are "rich"** (procedure + equipment + capability + description all present) → **perfect candidates for two-model LLM TrustScorer pre-compute** (matches spec target of 100-200)
- 9,738 sparse facilities → rule-based scoring (friend's approach fits perfectly here)

→ **Hybrid strategy validated:** LLM on rich rows + rules on sparse rows = best of both paths.

### 4. Silver table created — `workspace.default.silver_facilities`
- 10,000 rows
- Cleaned + parsed (JSON arrays → ARRAY<STRING>)
- VF trust meta-signals preserved
- All `try_cast` for numeric fields
- Raw JSON text kept for downstream LLM consumption

Schema highlights:
- `specialties`, `procedures`, `equipment`, `capabilities` — proper ARRAY columns
- `lat`, `lon`, `pincode` typed
- `social_count`, `has_logo`, `has_staff_presence`, `n_facts`, `social_followers`, `last_page_update`

### 5. Gold table — `workspace.default.gold_trust_rules` (rule-based, all 10k)
- 10,000 rows scored
- Components:
  - `completeness_score` (8 fields filled / 8)
  - `consistency_score` (rule-based contradictions: claim vs evidence)
  - `digital_credibility_score` (logo + staff + social)
  - `freshness_score` (days since last_page_update)
- `trust_score` = weighted sum (30% complete + 30% consistent + 20% digital + 20% fresh)
- 4 factor proxies (when no LLM): `p_bed_proxy`, `p_oxygen_proxy`, `p_specialist_proxy`, `p_drug_proxy`

Distribution:
- 0.6-0.8 (high): 705 facilities
- 0.4-0.6 (medium): 7,971
- 0.2-0.4 (low): 1,324
- (none above 0.8 — strict thresholds, expected for rule-only path; LLM scoring will push some up)

### 6. NGO Desert Map — `workspace.default.gold_pin_capabilities`
- 4,964 unique PIN codes
- Per-PIN counts of: cardiology, nephrology/dialysis, oncology, emergency, pediatric, OBGYN, orthopedic
- 2,121 PINs flagged as `is_specialty_desert` (43%)

**Killer demo numbers:**
- 4,793 PIN codes have **zero oncology** facilities
- 4,804 PIN codes have **zero dialysis**
- 4,637 PIN codes have **zero emergency medicine**

**State-level oncology gap (top deserts):**
| State | PINs | Total facilities | Oncology gap PINs | Dialysis gap | Emergency gap |
|---|---|---|---|---|---|
| Maharashtra | 644 | 1506 | 611 | 612 | 605 |
| Kerala | 479 | 597 | 471 | 473 | 464 |
| Uttar Pradesh | 424 | 1058 | 407 | 405 | 373 |
| Tamil Nadu | 357 | 630 | 343 | 346 | 333 |
| West Bengal | 302 | 483 | 295 | 294 | 293 |
| Bihar | 198 | 429 | 194 | 192 | 175 |

**Demo lines ready:**
- *"Bihar — 194 PIN codes with zero oncology facilities. 175 with zero emergency medicine."*
- *"Maharashtra has 1,506 facilities but 611 PIN codes have zero oncology. Density doesn't equal coverage."*

### 7. LLM TrustScorer pipeline — tested end-to-end
- Endpoint: `databricks-meta-llama-3-3-70b-instruct`
- Tested with sample hospital (cardiology + emergency, equipment list)
- **Returned clean JSON** with per-factor probabilities + reasoning
- Token usage: 338 tokens per call (200 prompt + 134 completion)
- Cost estimate: 200 hospitals × 4 factors × 338 tokens ≈ 270k tokens — under $5 even at premium rates

Sample response (from real test):
```json
{
  "p_bed": 0.8,
  "p_oxygen": 0.9,
  "p_drug_cardiac": 0.7,
  "p_specialist_cardiology": 0.9,
  "reasoning": "The facility has ... necessary equipment like oxygen pipeline and ventilator, indicating high probability ..."
}
```

---

## ⏭ Next steps (in order)

### ✓ 8. LLM TrustScorer Gold table — DONE
- Processed 262 rich hospitals → 256 successful (6 timeouts, retryable)
- Llama 3.3 70B via Foundation Model APIs, parallel 10 workers, 266s total
- 138,467 tokens used (~$0.30 — negligible against $400 trial)
- 0% parse errors — all 256 returned clean JSON
- Written to `workspace.default.gold_trust_llm`
- Distribution: 1 ≥0.9, 51 in 0.8-0.9, 82 in 0.7-0.8, 58 in 0.6-0.7, 27 in 0.5-0.6, 37 <0.5
- Top hospital: **INHS Sanjivani (Kochi) — Trust 0.90** (LLM-verified across 4 factors)

### ✓ 9. Hybrid `gold_trust_final` — DONE
- 10,000 rows total
- 256 `llm-verified` (avg trust 0.659, range 0.25-0.90)
- 9,744 `rule-inferred` (avg trust 0.456, range 0.25-0.70)
- Per-factor scores: `p_bed`, `p_oxygen`, `p_drug`, `p_specialist` — LLM where available, rule proxies elsewhere
- `trust_source` column drives UI badge: "Two-model verified" vs "Inferred from data"
- LLM `reasoning` column ready for click-to-source modal

### 10. Vector Search index for retrieval
- Create endpoint (Trial: 1 endpoint, 1 VS unit, Delta-sync)
- Index `silver_facilities.description + capabilities` joined text
- Embedding model: `databricks-bge-large-en` (already available)
- Used by: TriageAgent (symptom→specialty), Validator (similar past cases)

### 11. Atomic Booking transaction skeleton
- Create empty tables: `bed_reservations`, `ambulance_dispatches`, `doctor_slots`, `drug_reservations`
- Test 4-way Delta transaction with rollback semantics
- Confirm ACID guarantees on stage

### 12. Outcome feedback append-only table
- `outcome_feedback (patient_id, hospital_id, factor, actual_value, ts)`
- Schema only at this stage; ingestion comes from React UI later

### 13. Agent Reputation Score view
- View aggregating outcome_feedback into per-hospital `reputation_score`
- Used to adjust trust ceiling

---

## Open items / decisions for Tero

1. **GPT-5.5 quota:** demo invocation hit "rate limit 0" — need to check if Trial includes GPT-5.5 with usable quota. **Action:** call `databricks-gpt-5-5` from a notebook (different rate limit pool?) or pick second model from a different family.
2. **Two-model pair choice:** options are
   - Llama 3.3 70B + GPT-5.5 (different families, GPT quota uncertain)
   - Llama 3.3 70B + Llama 4 Maverick (same family — weaker independence)
   - Llama 3.3 70B + Qwen3 80B (different families, Chinese-trained — interesting but untested for our task)
   - Llama 3.3 70B + Gemma 3 12B (different families, smaller validator)
   - **Recommendation:** start with Llama 3.3 + Llama 4 Maverick (both work, similar latency); upgrade Validator to GPT-5.5 if quota check succeeds.
3. **Vector Search storage-optimized index:** need to create one and confirm it's available in our region. Falls back to local FAISS in spec.
4. **Friend's plan fold:** his rule-based approach already lives in `gold_trust_rules`. His Alert Agent is unique (not in our spec) — should we fold it as a Layer-2 enhancement?

---

## Tables created

| Table | Rows | Purpose |
|---|---|---|
| `workspace.default.vf_hackathon_dataset_india_large` | 10,000 | Bronze — raw VF |
| `workspace.default.silver_facilities` | 10,000 | Silver — cleaned + parsed |
| `workspace.default.gold_trust_rules` | 10,000 | Gold — rule-based Trust + 4 factor proxies |
| `workspace.default.gold_pin_capabilities` | 3,736 | Gold — NGO Desert Map aggregation (current build; previous lost workspace had 4964) |
| `workspace.default.gold_trust_llm` | 256 | Gold — LLM-extracted Trust on rich hospitals (Llama 3.3 70B) |
| `workspace.default.gold_trust_llm_v2` | 255 | Gold — second-model LLM scoring (Llama 4 Maverick, Validator role) |
| `workspace.default.gold_trust_two_model` | 262 | Gold — joined v1+v2 with agreement metrics (max_factor_disagreement, verification_status) |
| `workspace.default.gold_trust_final` | 10,000 | Gold — **HYBRID** with 4-tier badge: two-model-verified (80) / models-disagree (169) / llm-verified (13) / rule-inferred (9738) |
| `workspace.default.txn_atomic` | 6 (seed) | Atomic booking ledger (saga-commit pattern) |
| `workspace.default.bed_reservations` | 6 (seed) | Per-bed Delta table |
| `workspace.default.ambulance_dispatches` | 5 (seed) | Per-vehicle Delta table |
| `workspace.default.doctor_slots` | 5 (seed) | Per-slot Delta table |
| `workspace.default.drug_reservations` | 5 (seed) | Per-drug Delta table |
| `workspace.default.outcome_feedback` | 14 (seed) | Append-only patient ping ledger |
| `workspace.default.silver_facilities_text` | 10,000 | Concatenated text per facility for vector embedding |
| `workspace.default.silver_facilities_text_idx` | provisioning | Vector Search Delta-sync index (BGE-large) |

**Views:**
- `v_committed_bookings` — only COMMITTED transactions visible (rolled-back filtered)
- `v_agent_reputation` — per-hospital reputation_score from outcomes
- `v_trust_calibrated` — gold_trust_final adjusted by reputation when n_outcomes ≥ 5

## Reproducible rebuild

All tables rebuilt from `data/VF_Hackathon_Dataset_India_Large.xlsx` + `data/llm_artifacts/*.jsonl` via:

```bash
# core data layer
DBX_PROFILE=tero2 python3 scripts/databricks/00_bronze_ingest.py
python3 scripts/databricks/run_sql_file.py scripts/databricks/01_silver.sql
python3 scripts/databricks/run_sql_file.py scripts/databricks/02_gold_rules.sql
python3 scripts/databricks/run_sql_file.py scripts/databricks/03_gold_desert.sql
python3 scripts/databricks/04_gold_llm.py
python3 scripts/databricks/04b_gold_llm_v2.py
python3 scripts/databricks/run_sql_file.py scripts/databricks/05_gold_hybrid.sql
python3 scripts/databricks/run_sql_file.py scripts/databricks/10_two_model_verify.sql
# atomic booking + outcome
python3 scripts/databricks/run_sql_file.py scripts/databricks/07_atomic_booking.sql
python3 scripts/databricks/run_sql_file.py scripts/databricks/08_outcome_feedback.sql
python3 scripts/databricks/run_sql_file.py scripts/databricks/09_demo_seed.sql
# vector search (10-30 min initial sync)
python3 scripts/databricks/06_vector_search.py
```

Total time: ~5-10 minutes for tables + 10-30 min for VS index initial sync.

## Demo flow assets ready

- **Two-model verified tier (80 hospitals)** — query: `SELECT name, city, state, trust_score FROM gold_trust_final WHERE trust_source='two-model-verified' ORDER BY trust_score DESC LIMIT 10`
- **Models-disagree tier (169 hospitals)** — examples where Llama 3.3 + Llama 4 Maverick differ by >0.20 on at least one factor → flagged as low-confidence in UI
- **NGO Desert headlines** — Bihar 149 PINs zero oncology, Maharashtra 1492 facilities/403 zero oncology
- **Atomic booking demo** — `SELECT * FROM v_committed_bookings ORDER BY transaction_id` shows 5 successful 4-way bookings; `SELECT * FROM txn_atomic WHERE status='ROLLED_BACK'` shows the 1 saga rollback (ambulance unavailable)
- **Outcome learning loop** — `SELECT * FROM v_trust_calibrated WHERE total_outcomes > 0` shows INHS Sanjivani Kochi at 6 outcomes, reputation 1.0, trust holds 0.888 (two-model-verified)

## Resources used

- SQL warehouse: `10fff96dd6d936b5` (Serverless Starter Small, RUNNING)
- Foundation Model APIs called: 256 hospitals × Llama 3.3 70B (138K tokens, ~$0.30) — JSONL preserved in repo
- UC Volume: `workspace.default.raw` (parquet staging)
- Storage: ~5 MB (Bronze 4.5 MB parquet + LLM 252 KB JSONL + Delta tables)
- Cost so far: negligible (well under $1 of the $400 trial credit)
