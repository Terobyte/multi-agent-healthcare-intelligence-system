-- gold_trust_final: HYBRID trust source-of-truth
-- 256 hospitals get LLM-verified scores (Llama 3.3 70B per-factor probabilities)
-- 9744 facilities get rule-inferred scores (proxies from facility metadata)
-- ui badge: trust_source = 'llm-verified' | 'rule-inferred'
-- click-to-source modal pulls reasoning column for the 256 verified rows

CREATE OR REPLACE TABLE workspace.default.gold_trust_final AS
SELECT
  r.facility_id,
  r.name,
  r.city,
  r.state,
  r.pincode,
  r.facility_type,
  -- per-factor scores: prefer LLM, fall back to rule proxy
  COALESCE(l.p_bed,        r.p_bed_proxy)         AS p_bed,
  COALESCE(l.p_oxygen,     r.p_oxygen_proxy)      AS p_oxygen,
  COALESCE(l.p_drug,       r.p_drug_proxy)        AS p_drug,
  COALESCE(l.p_specialist, r.p_specialist_proxy)  AS p_specialist,
  -- overall trust: LLM avg of 4 factors when available, else rule blended trust
  CASE
    WHEN l.facility_id IS NOT NULL THEN ROUND((l.p_bed + l.p_oxygen + l.p_drug + l.p_specialist) / 4.0, 3)
    ELSE r.trust_score
  END AS trust_score,
  -- ui badge
  CASE WHEN l.facility_id IS NOT NULL THEN 'llm-verified' ELSE 'rule-inferred' END AS trust_source,
  l.ci             AS llm_confidence,
  l.reasoning,
  l.model_endpoint,
  l.tokens         AS llm_tokens,
  -- carry forward useful columns for routing
  r.num_doctors, r.capacity, r.lat, r.lon,
  r.specialties, r.procedures, r.equipment, r.capabilities,
  r.completeness_score, r.consistency_score, r.digital_credibility_score, r.freshness_score
FROM workspace.default.gold_trust_rules r
LEFT JOIN workspace.default.gold_trust_llm l
  ON r.facility_id = l.facility_id;
