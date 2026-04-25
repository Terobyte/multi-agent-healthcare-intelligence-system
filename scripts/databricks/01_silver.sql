-- silver: clean facilities with parsed json arrays + trust meta-signals
-- input:  workspace.default.vf_hackathon_dataset_india_large (10000 rows × 41 cols)
-- output: workspace.default.silver_facilities (10000 rows, typed)
-- notes:
--   - facility_id = ROW_NUMBER over name (stable: all 10000 names are unique)
--   - all object cols arrived as strings from xlsx; try_cast for safety
--   - keep raw_*_json for downstream LLM ingestion

CREATE OR REPLACE TABLE workspace.default.silver_facilities AS
SELECT
  CAST(ROW_NUMBER() OVER (ORDER BY name) AS STRING)            AS facility_id,
  name,
  address_city                                                  AS city,
  address_stateOrRegion                                         AS state,
  address_zipOrPostcode                                         AS pincode,
  address_country                                               AS country,
  facilityTypeId                                                AS facility_type,
  operatorTypeId                                                AS operator_type,
  description,
  -- parsed array columns
  from_json(specialties, 'ARRAY<STRING>')                       AS specialties,
  from_json(procedure,   'ARRAY<STRING>')                       AS procedures,
  from_json(equipment,   'ARRAY<STRING>')                       AS equipment,
  from_json(capability,  'ARRAY<STRING>')                       AS capabilities,
  from_json(phone_numbers,'ARRAY<STRING>')                      AS phones,
  from_json(websites,    'ARRAY<STRING>')                       AS websites_all,
  -- raw json text for LLM consumption (no parsing loss)
  specialties                                                   AS raw_specialties_json,
  procedure                                                     AS raw_procedure_json,
  equipment                                                     AS raw_equipment_json,
  capability                                                    AS raw_capability_json,
  -- typed numerics (xlsx loaded everything as string)
  try_cast(numberDoctors AS DOUBLE)                             AS num_doctors,
  try_cast(capacity      AS DOUBLE)                             AS capacity,
  try_cast(latitude      AS DOUBLE)                             AS lat,
  try_cast(longitude     AS DOUBLE)                             AS lon,
  try_cast(yearEstablished AS INT)                              AS year_established,
  -- trust meta-signals (vf schema)
  try_cast(distinct_social_media_presence_count AS INT)         AS social_count,
  CASE WHEN lower(custom_logo_presence) IN ('true','1','yes')   THEN TRUE
       WHEN lower(custom_logo_presence) IN ('false','0','no')   THEN FALSE
       ELSE NULL END                                            AS has_logo,
  CASE WHEN lower(affiliated_staff_presence) IN ('true','1','yes') THEN TRUE
       WHEN lower(affiliated_staff_presence) IN ('false','0','no') THEN FALSE
       ELSE NULL END                                            AS has_staff_presence,
  try_cast(number_of_facts_about_the_organization AS INT)       AS n_facts,
  try_cast(engagement_metrics_n_followers AS BIGINT)            AS social_followers,
  try_cast(engagement_metrics_n_likes AS BIGINT)                AS social_likes,
  try_cast(post_metrics_post_count AS INT)                      AS post_count,
  recency_of_page_update                                        AS last_page_update_raw,
  post_metrics_most_recent_social_media_post_date               AS last_post_date_raw,
  officialPhone, officialWebsite, email
FROM workspace.default.vf_hackathon_dataset_india_large;
