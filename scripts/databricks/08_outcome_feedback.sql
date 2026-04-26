-- outcome_feedback: append-only ledger of post-visit ground truth
-- patient pings T+2h after a booking — was the bed/oxygen/drug/specialist actually delivered?
-- this table is the input to the Outcome Learning Loop: aggregated per-hospital reputation_score
-- adjusts the trust ceiling so a hospital that consistently fails outcomes can never score above
-- the empirical ceiling, regardless of LLM optimism.
--
-- design rules:
--   - append-only (never UPDATE / DELETE — corrections come as new rows with newer ts)
--   - patient_id is opaque hash (not PII)
--   - factor matches gold_trust_final.p_* columns: bed | oxygen | drug | specialist
--   - actual_value: 1.0 = delivered, 0.0 = absent, 0.5 = partial
--   - source: how the outcome was captured (sms | voice | nurse_note | ngo_visit)

CREATE OR REPLACE TABLE workspace.default.outcome_feedback (
  feedback_id        STRING NOT NULL,
  transaction_id     STRING,                -- links back to txn_atomic if booking-driven
  patient_id         STRING NOT NULL,
  facility_id        STRING NOT NULL,
  factor             STRING NOT NULL,       -- bed | oxygen | drug | specialist
  actual_value       DOUBLE NOT NULL,       -- 1.0 / 0.0 / 0.5
  llm_predicted      DOUBLE,                -- what gold_trust_final said at booking time (joined-in for delta calc)
  source             STRING,                -- sms | voice | nurse_note | ngo_visit
  notes              STRING,                -- free-text from patient or worker
  ts                 TIMESTAMP NOT NULL,
  CONSTRAINT outcome_pk PRIMARY KEY (feedback_id)
) TBLPROPERTIES (delta.enableChangeDataFeed = true);

-- agent_reputation: per-hospital aggregation derived from outcome_feedback
-- reputation_score = empirical hit rate (mean actual_value) per hospital
-- n_outcomes ≥ 5 → reliable; below that, fall back to llm/rule trust
-- this view is used by the Trust Layer to cap ceiling: trust_score = min(llm_trust, reputation_ceiling)

-- design note on two-level aggregation:
-- we AVG per (facility, factor) first, then AVG across factors.
-- this gives equal weight to every factor (bed/oxygen/drug/specialist) regardless
-- of how many pings a hospital got per factor. without per-factor first, a hospital
-- with 10 bed pings + 1 specialist ping would let the bed signal drown out specialist.
-- intentional — do not collapse to a flat AVG(actual_value) across all rows.
CREATE OR REPLACE VIEW workspace.default.v_agent_reputation AS
WITH per_facility AS (
  SELECT
    facility_id,
    factor,
    COUNT(*)                                     AS n_outcomes,
    AVG(actual_value)                            AS observed_rate,
    AVG(actual_value - coalesce(llm_predicted, 0.5)) AS llm_delta,
    MAX(ts)                                      AS last_outcome_ts
  FROM workspace.default.outcome_feedback
  GROUP BY facility_id, factor
)
SELECT
  facility_id,
  -- aggregate across all 4 factors (equal-weight per factor, see note above)
  SUM(n_outcomes)                                                AS total_outcomes,
  ROUND(AVG(observed_rate), 3)                                   AS reputation_score,
  -- per-factor breakdown for explainability
  MAX(CASE WHEN factor='bed'        THEN observed_rate END)      AS bed_observed,
  MAX(CASE WHEN factor='oxygen'     THEN observed_rate END)      AS oxygen_observed,
  MAX(CASE WHEN factor='drug'       THEN observed_rate END)      AS drug_observed,
  MAX(CASE WHEN factor='specialist' THEN observed_rate END)      AS specialist_observed,
  ROUND(AVG(llm_delta), 3)                                       AS avg_llm_calibration_error,
  MAX(last_outcome_ts)                                           AS last_outcome_ts
FROM per_facility
GROUP BY facility_id;

-- v_trust_calibrated: gold_trust_final adjusted by reputation when n_outcomes ≥ 5
-- after 10_two_model_verify.sql, gold_trust_final has llama_3_3_reasoning + llama_4_reasoning
-- + max_factor_disagreement instead of single reasoning column
CREATE OR REPLACE VIEW workspace.default.v_trust_calibrated AS
SELECT
  g.facility_id, g.name, g.city, g.state, g.facility_type,
  g.trust_score                                AS trust_raw,
  g.trust_source,                                  -- two-model-verified | models-disagree | llm-verified | rule-inferred
  g.max_factor_disagreement,
  r.reputation_score,
  r.total_outcomes,
  CASE
    WHEN r.total_outcomes >= 5 THEN least(g.trust_score, r.reputation_score + 0.10)
    ELSE g.trust_score
  END                                           AS trust_calibrated,
  r.avg_llm_calibration_error,
  g.p_bed, g.p_oxygen, g.p_drug, g.p_specialist,
  g.llama_3_3_reasoning, g.llama_4_reasoning,
  g.lat, g.lon
FROM workspace.default.gold_trust_final g
LEFT JOIN workspace.default.v_agent_reputation r
  ON g.facility_id = r.facility_id;
