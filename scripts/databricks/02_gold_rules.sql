-- gold_trust_rules: rule-based trust scoring for ALL 10000 facilities
-- input:  workspace.default.silver_facilities
-- output: workspace.default.gold_trust_rules (10000 rows)
-- formula:
--   completeness    = filled_fields / 8        (0..1)
--   consistency     = 1 - contradictions/4     (0..1)
--   digital         = logo_w + staff_w + social_w (0..1)
--   freshness       = recency proxy            (0..1, default 0.5 when unparseable)
--   trust_score     = 0.30*comp + 0.30*cons + 0.20*digital + 0.20*freshness
-- + 4 factor proxies (p_bed/p_oxygen/p_specialist/p_drug) used when no llm score is available

CREATE OR REPLACE TABLE workspace.default.gold_trust_rules AS
WITH base AS (
  SELECT
    facility_id, name, city, state, pincode, facility_type,
    description, specialties, procedures, equipment, capabilities,
    num_doctors, capacity, lat, lon,
    has_logo, has_staff_presence, social_count, n_facts, social_followers,
    last_page_update_raw,
    -- denormalised flags for scoring
    CASE WHEN description IS NOT NULL AND description <> '' THEN 1 ELSE 0 END AS has_desc,
    CASE WHEN size(specialties) > 0  THEN 1 ELSE 0 END AS has_specs,
    CASE WHEN size(procedures)  > 0  THEN 1 ELSE 0 END AS has_procs,
    CASE WHEN size(equipment)   > 0  THEN 1 ELSE 0 END AS has_equip,
    CASE WHEN size(capabilities)> 0  THEN 1 ELSE 0 END AS has_caps,
    CASE WHEN num_doctors IS NOT NULL AND num_doctors > 0 THEN 1 ELSE 0 END AS has_doc,
    CASE WHEN capacity IS NOT NULL AND capacity > 0 THEN 1 ELSE 0 END AS has_cap,
    CASE WHEN lat IS NOT NULL AND lon IS NOT NULL THEN 1 ELSE 0 END AS has_geo
  FROM workspace.default.silver_facilities
),
scored AS (
  SELECT *,
    -- completeness: 8 fields filled
    (has_desc + has_specs + has_procs + has_equip + has_caps + has_doc + has_cap + has_geo) / 8.0 AS completeness_score,
    -- consistency: count contradictions (claim vs evidence)
    1.0 - (
      (CASE WHEN facility_type = 'hospital' AND has_specs = 0 THEN 1 ELSE 0 END) +
      (CASE WHEN size(filter(specialties, s -> lower(s) LIKE '%surg%')) > 0 AND has_equip = 0 THEN 1 ELSE 0 END) +
      (CASE WHEN size(filter(specialties, s -> lower(s) LIKE '%emergency%')) > 0 AND has_doc = 0 THEN 1 ELSE 0 END) +
      (CASE WHEN facility_type = 'hospital' AND has_cap = 0 THEN 1 ELSE 0 END)
    ) / 4.0 AS consistency_score,
    -- digital credibility: logo + staff + social
    (
      (CASE WHEN has_logo = TRUE THEN 0.3 ELSE 0 END) +
      (CASE WHEN has_staff_presence = TRUE THEN 0.4 ELSE 0 END) +
      (CASE WHEN coalesce(social_count, 0) >= 1 THEN 0.3 ELSE 0 END)
    ) AS digital_credibility_score,
    -- freshness: parse "Updated NN days ago" patterns from last_page_update_raw
    CASE
      WHEN last_page_update_raw RLIKE '(?i)today|hour|minute' THEN 1.0
      WHEN last_page_update_raw RLIKE '(?i)([0-9]+) day' THEN
        greatest(0.0, 1.0 - try_cast(regexp_extract(last_page_update_raw, '([0-9]+)', 1) AS DOUBLE) / 365.0)
      WHEN last_page_update_raw RLIKE '(?i)([0-9]+) month' THEN
        greatest(0.0, 1.0 - try_cast(regexp_extract(last_page_update_raw, '([0-9]+)', 1) AS DOUBLE) / 12.0)
      WHEN last_page_update_raw RLIKE '(?i)([0-9]+) year' THEN
        greatest(0.0, 1.0 - try_cast(regexp_extract(last_page_update_raw, '([0-9]+)', 1) AS DOUBLE) * 0.5)
      ELSE 0.5
    END AS freshness_score
  FROM base
)
SELECT
  facility_id, name, city, state, pincode, facility_type,
  completeness_score,
  consistency_score,
  digital_credibility_score,
  freshness_score,
  -- weighted trust
  round(
    0.30 * completeness_score +
    0.30 * consistency_score +
    0.20 * digital_credibility_score +
    0.20 * freshness_score
  , 3) AS trust_score,
  -- 4 factor proxies (rule-based fallback when no llm)
  CASE
    WHEN facility_type = 'hospital' AND has_cap = 1 THEN 0.6
    WHEN facility_type = 'hospital' THEN 0.4
    WHEN facility_type = 'clinic' AND has_cap = 1 THEN 0.4
    ELSE 0.2
  END AS p_bed_proxy,
  CASE
    WHEN size(filter(equipment, e -> lower(e) RLIKE '(oxygen|ventilator|o2)')) > 0 THEN 0.7
    WHEN facility_type = 'hospital' THEN 0.4
    ELSE 0.2
  END AS p_oxygen_proxy,
  CASE
    WHEN num_doctors IS NOT NULL AND num_doctors >= 5 THEN 0.7
    WHEN num_doctors IS NOT NULL AND num_doctors >= 1 THEN 0.5
    WHEN size(specialties) >= 3 THEN 0.5
    WHEN facility_type = 'hospital' THEN 0.4
    ELSE 0.25
  END AS p_specialist_proxy,
  CASE
    WHEN facility_type IN ('pharmacy', 'farmacy') THEN 0.8
    WHEN facility_type = 'hospital' THEN 0.5
    ELSE 0.3
  END AS p_drug_proxy,
  -- carry forward useful columns
  num_doctors, capacity, lat, lon, specialties, procedures, equipment, capabilities,
  has_logo, has_staff_presence, social_count
FROM scored;
