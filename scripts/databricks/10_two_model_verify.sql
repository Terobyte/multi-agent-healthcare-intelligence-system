-- two-model verification: independent error modes via Llama 3.3 70B + Llama 4 Maverick
-- per-row max disagreement across 4 factors → "two-model-verified" badge if ≤ 0.20
-- this gives the demo a defensible "we don't trust a single model — we cross-check" line.
--
-- output:
--   gold_trust_two_model — joined per-facility scores from both models + agreement metrics
--   gold_trust_final     — REWRITTEN to use blended/two-model logic where both models present

CREATE OR REPLACE TABLE workspace.default.gold_trust_two_model AS
SELECT
  COALESCE(v1.facility_id, v2.facility_id) AS facility_id,
  COALESCE(v1.name, v2.name)               AS name,
  -- per-factor v1 (Llama 3.3 70B = Extractor)
  v1.p_bed         AS v1_p_bed,
  v1.p_oxygen      AS v1_p_oxygen,
  v1.p_drug        AS v1_p_drug,
  v1.p_specialist  AS v1_p_specialist,
  v1.ci            AS v1_ci,
  v1.reasoning     AS v1_reasoning,
  -- per-factor v2 (Llama 4 Maverick = Validator)
  v2.p_bed         AS v2_p_bed,
  v2.p_oxygen      AS v2_p_oxygen,
  v2.p_drug        AS v2_p_drug,
  v2.p_specialist  AS v2_p_specialist,
  v2.ci            AS v2_ci,
  v2.reasoning     AS v2_reasoning,
  -- agreement metrics (only when both present)
  CASE WHEN v1.facility_id IS NOT NULL AND v2.facility_id IS NOT NULL
       THEN GREATEST(
              ABS(v1.p_bed        - v2.p_bed),
              ABS(v1.p_oxygen     - v2.p_oxygen),
              ABS(v1.p_drug       - v2.p_drug),
              ABS(v1.p_specialist - v2.p_specialist)
            )
       ELSE NULL
  END AS max_factor_disagreement,
  CASE WHEN v1.facility_id IS NOT NULL AND v2.facility_id IS NOT NULL
       THEN ROUND((
              ABS(v1.p_bed        - v2.p_bed) +
              ABS(v1.p_oxygen     - v2.p_oxygen) +
              ABS(v1.p_drug       - v2.p_drug) +
              ABS(v1.p_specialist - v2.p_specialist)
            ) / 4.0, 3)
       ELSE NULL
  END AS avg_factor_disagreement,
  -- two-model-verified badge: both models present + max factor delta ≤ 0.2
  CASE
    WHEN v1.facility_id IS NULL OR v2.facility_id IS NULL THEN 'single-model'
    WHEN GREATEST(
            ABS(v1.p_bed        - v2.p_bed),
            ABS(v1.p_oxygen     - v2.p_oxygen),
            ABS(v1.p_drug       - v2.p_drug),
            ABS(v1.p_specialist - v2.p_specialist)
         ) <= 0.20 THEN 'two-model-verified'
    ELSE 'models-disagree'
  END AS verification_status,
  -- conservative blended scores:
  -- if both models agree (max factor delta ≤ 0.20) → average them (signal smoothing)
  -- if models disagree → use MIN (conservative — never inflate trust on disagreement)
  -- if only one present → use whichever
  CASE
    WHEN v1.p_bed IS NOT NULL AND v2.p_bed IS NOT NULL AND
         GREATEST(ABS(v1.p_bed-v2.p_bed),ABS(v1.p_oxygen-v2.p_oxygen),ABS(v1.p_drug-v2.p_drug),ABS(v1.p_specialist-v2.p_specialist)) <= 0.20
      THEN (v1.p_bed + v2.p_bed) / 2.0
    WHEN v1.p_bed IS NOT NULL AND v2.p_bed IS NOT NULL THEN LEAST(v1.p_bed, v2.p_bed)
    ELSE COALESCE(v1.p_bed, v2.p_bed)
  END AS p_bed_blended,
  CASE
    WHEN v1.p_oxygen IS NOT NULL AND v2.p_oxygen IS NOT NULL AND
         GREATEST(ABS(v1.p_bed-v2.p_bed),ABS(v1.p_oxygen-v2.p_oxygen),ABS(v1.p_drug-v2.p_drug),ABS(v1.p_specialist-v2.p_specialist)) <= 0.20
      THEN (v1.p_oxygen + v2.p_oxygen) / 2.0
    WHEN v1.p_oxygen IS NOT NULL AND v2.p_oxygen IS NOT NULL THEN LEAST(v1.p_oxygen, v2.p_oxygen)
    ELSE COALESCE(v1.p_oxygen, v2.p_oxygen)
  END AS p_oxygen_blended,
  CASE
    WHEN v1.p_drug IS NOT NULL AND v2.p_drug IS NOT NULL AND
         GREATEST(ABS(v1.p_bed-v2.p_bed),ABS(v1.p_oxygen-v2.p_oxygen),ABS(v1.p_drug-v2.p_drug),ABS(v1.p_specialist-v2.p_specialist)) <= 0.20
      THEN (v1.p_drug + v2.p_drug) / 2.0
    WHEN v1.p_drug IS NOT NULL AND v2.p_drug IS NOT NULL THEN LEAST(v1.p_drug, v2.p_drug)
    ELSE COALESCE(v1.p_drug, v2.p_drug)
  END AS p_drug_blended,
  CASE
    WHEN v1.p_specialist IS NOT NULL AND v2.p_specialist IS NOT NULL AND
         GREATEST(ABS(v1.p_bed-v2.p_bed),ABS(v1.p_oxygen-v2.p_oxygen),ABS(v1.p_drug-v2.p_drug),ABS(v1.p_specialist-v2.p_specialist)) <= 0.20
      THEN (v1.p_specialist + v2.p_specialist) / 2.0
    WHEN v1.p_specialist IS NOT NULL AND v2.p_specialist IS NOT NULL THEN LEAST(v1.p_specialist, v2.p_specialist)
    ELSE COALESCE(v1.p_specialist, v2.p_specialist)
  END AS p_specialist_blended,
  -- carry forward token usage / confidence so downstream UI can show "verified by 2 models, X tokens spent"
  v1.tokens AS v1_tokens,
  v2.tokens AS v2_tokens,
  v1.model_endpoint AS v1_model,
  v2.model_endpoint AS v2_model
FROM workspace.default.gold_trust_llm v1
FULL OUTER JOIN workspace.default.gold_trust_llm_v2 v2
  ON v1.facility_id = v2.facility_id;

-- rewrite gold_trust_final using blended two-model scores when available
CREATE OR REPLACE TABLE workspace.default.gold_trust_final AS
SELECT
  r.facility_id, r.name, r.city, r.state, r.pincode, r.facility_type,
  -- per-factor: prefer blended (two-model), then single-model, then rule proxy
  COALESCE(t.p_bed_blended,        r.p_bed_proxy)        AS p_bed,
  COALESCE(t.p_oxygen_blended,     r.p_oxygen_proxy)     AS p_oxygen,
  COALESCE(t.p_drug_blended,       r.p_drug_proxy)       AS p_drug,
  COALESCE(t.p_specialist_blended, r.p_specialist_proxy) AS p_specialist,
  -- overall trust
  CASE
    WHEN t.facility_id IS NOT NULL
      THEN ROUND((t.p_bed_blended + t.p_oxygen_blended + t.p_drug_blended + t.p_specialist_blended) / 4.0, 3)
    ELSE r.trust_score
  END AS trust_score,
  -- ui badge — three tiers now
  CASE
    WHEN t.verification_status = 'two-model-verified' THEN 'two-model-verified'
    WHEN t.verification_status = 'models-disagree'    THEN 'models-disagree'
    WHEN t.verification_status = 'single-model'       THEN 'llm-verified'
    ELSE 'rule-inferred'
  END AS trust_source,
  t.max_factor_disagreement,
  t.avg_factor_disagreement,
  t.v1_reasoning AS llama_3_3_reasoning,
  t.v2_reasoning AS llama_4_reasoning,
  -- llm metadata (carried forward to gold_trust_final so downstream consumers can read it)
  COALESCE(t.v1_tokens, 0) + COALESCE(t.v2_tokens, 0) AS llm_tokens,
  CASE
    WHEN t.v1_model IS NOT NULL AND t.v2_model IS NOT NULL THEN concat(t.v1_model, '+', t.v2_model)
    ELSE COALESCE(t.v1_model, t.v2_model)
  END AS model_endpoint,
  -- llm_confidence: Llama 3.3 ci field if present, else Maverick's
  COALESCE(t.v1_ci, t.v2_ci) AS llm_confidence,
  r.num_doctors, r.capacity, r.lat, r.lon,
  r.specialties, r.procedures, r.equipment, r.capabilities,
  r.completeness_score, r.consistency_score, r.digital_credibility_score, r.freshness_score
FROM workspace.default.gold_trust_rules r
LEFT JOIN workspace.default.gold_trust_two_model t
  ON r.facility_id = t.facility_id;
