-- gold_pin_capabilities: NGO Medical Desert Map per PIN code
-- input:  workspace.default.silver_facilities
-- output: workspace.default.gold_pin_capabilities (~5000 PINs)
-- per pin: facility count + capability counts per specialty + desert flags
-- demo target: identify pin codes with zero coverage for life-critical specialties

CREATE OR REPLACE TABLE workspace.default.gold_pin_capabilities AS
WITH per_facility AS (
  SELECT
    facility_id,
    pincode,
    state,
    facility_type,
    -- specialty match flags (any element matches keyword pattern)
    CASE WHEN size(filter(specialties, s -> lower(s) RLIKE '(cardio|cardiac|heart)')) > 0 THEN 1 ELSE 0 END AS has_cardio,
    CASE WHEN size(filter(specialties, s -> lower(s) RLIKE '(nephro|dialys|renal)')) > 0 THEN 1 ELSE 0 END AS has_dialysis,
    CASE WHEN size(filter(specialties, s -> lower(s) RLIKE '(oncol|cancer|tumor|chemo|radiotherapy)')) > 0 THEN 1 ELSE 0 END AS has_oncology,
    CASE WHEN size(filter(specialties, s -> lower(s) RLIKE '(emergen|trauma|criticalcare)')) > 0 THEN 1 ELSE 0 END AS has_emergency,
    CASE WHEN size(filter(specialties, s -> lower(s) RLIKE '(pediatric|paediatr|neonat|child)')) > 0 THEN 1 ELSE 0 END AS has_pediatric,
    CASE WHEN size(filter(specialties, s -> lower(s) RLIKE '(obgyn|gynec|obstetric|maternit|womenshealth)')) > 0 THEN 1 ELSE 0 END AS has_obgyn,
    CASE WHEN size(filter(specialties, s -> lower(s) RLIKE '(orthoped|orthopaed|ortho)')) > 0 THEN 1 ELSE 0 END AS has_ortho
  FROM workspace.default.silver_facilities
  WHERE pincode IS NOT NULL AND pincode <> ''
)
SELECT
  pincode,
  any_value(state)               AS state,
  COUNT(*)                       AS n_facilities,
  SUM(CASE WHEN facility_type='hospital' THEN 1 ELSE 0 END) AS n_hospitals,
  SUM(has_cardio)                AS n_cardio,
  SUM(has_dialysis)              AS n_dialysis,
  SUM(has_oncology)              AS n_oncology,
  SUM(has_emergency)             AS n_emergency,
  SUM(has_pediatric)             AS n_pediatric,
  SUM(has_obgyn)                 AS n_obgyn,
  SUM(has_ortho)                 AS n_ortho,
  -- desert flag: missing >=2 of the 7 critical specialties
  CASE WHEN
    (CASE WHEN SUM(has_cardio)=0 THEN 1 ELSE 0 END +
     CASE WHEN SUM(has_dialysis)=0 THEN 1 ELSE 0 END +
     CASE WHEN SUM(has_oncology)=0 THEN 1 ELSE 0 END +
     CASE WHEN SUM(has_emergency)=0 THEN 1 ELSE 0 END +
     CASE WHEN SUM(has_pediatric)=0 THEN 1 ELSE 0 END +
     CASE WHEN SUM(has_obgyn)=0 THEN 1 ELSE 0 END +
     CASE WHEN SUM(has_ortho)=0 THEN 1 ELSE 0 END) >= 2
    THEN TRUE ELSE FALSE END    AS is_specialty_desert
FROM per_facility
GROUP BY pincode;
