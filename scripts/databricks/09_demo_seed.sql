-- demo seed: 5 atomic bookings + 1 ROLLED_BACK + 20 outcome pings
--
-- !!! DEMO-ONLY: uses INSERT OVERWRITE which wipes any existing booking/outcome rows. !!!
-- !!! Run only at the start of a demo dry-run, never against production data.         !!!
--
-- bookings target real LLM-verified high-trust hospitals from gold_trust_llm so the
-- "trust badge → booking → outcome → calibrated trust" story has a continuous thread.
--
-- two demo arcs:
--   A. INHS Sanjivani (5603): 6 positive outcomes → reputation 1.0 → trust holds at 0.888
--      "the system confirms the LLM was right"
--   B. Aradhna Super Speciality (959): 6 outcomes mostly negative → reputation ~0.33
--      → calibrated_trust caps from 0.831 down to ~0.43
--      "the system catches an over-optimistic LLM and self-corrects from outcomes"
--
-- facility map (trust shown is post-two-model-blend, gold_trust_final.trust_score):
--   5603 = INHS Sanjivani, Kochi (trust 0.888, two-model-verified)
--   2672 = Delhi Liver Transplant (trust 0.863, two-model-verified)
--   959  = Aradhna Super Speciality + Trauma Centre, Shamli UP (trust 0.831, two-model-verified) — calibration arc
--   881  = Apex Eye Care, Cuttack (trust 0.825, two-model-verified)
--   186  = Aadit Eye Hospital, Ahmedabad (trust 0.425, models-disagree — used for the disagreement story)
--   8888 = synthetic FAILED facility for the rollback story (rule-inferred)

-- 5 successful + 1 rolled-back atomic bookings
INSERT OVERWRITE workspace.default.txn_atomic VALUES
  ('txn_001','pat_kl_001','5603','COMMITTED', NULL, current_timestamp(), current_timestamp()),
  ('txn_002','pat_dl_001','2672','COMMITTED', NULL, current_timestamp(), current_timestamp()),
  ('txn_003','pat_gj_001','186', 'COMMITTED', NULL, current_timestamp(), current_timestamp()),
  ('txn_004','pat_up_001','959', 'COMMITTED', NULL, current_timestamp(), current_timestamp()),
  ('txn_005','pat_od_001','881', 'COMMITTED', NULL, current_timestamp(), current_timestamp()),
  ('txn_999','pat_xx_001','8888','ROLLED_BACK','ambulance unavailable - no vehicle in 30 km radius', current_timestamp(), current_timestamp());

INSERT OVERWRITE workspace.default.bed_reservations VALUES
  ('bed_001','txn_001','5603','ICU-3','icu','pat_kl_001', current_timestamp(), current_timestamp() + INTERVAL 24 HOURS, 'CONFIRMED', current_timestamp(), current_timestamp()),
  ('bed_002','txn_002','2672','Liver-Suite-2','private','pat_dl_001', current_timestamp(), current_timestamp() + INTERVAL 72 HOURS, 'CONFIRMED', current_timestamp(), current_timestamp()),
  ('bed_003','txn_003','186','Day-Care-5','general','pat_gj_001', current_timestamp(), current_timestamp() + INTERVAL 6 HOURS, 'CONFIRMED', current_timestamp(), current_timestamp()),
  ('bed_004','txn_004','959','Trauma-1','icu','pat_up_001', current_timestamp(), current_timestamp() + INTERVAL 48 HOURS, 'CONFIRMED', current_timestamp(), current_timestamp()),
  ('bed_005','txn_005','881','OPD-12','general','pat_od_001', current_timestamp(), current_timestamp() + INTERVAL 4 HOURS, 'CONFIRMED', current_timestamp(), current_timestamp()),
  ('bed_999','txn_999','8888','ICU-1','icu','pat_xx_001', current_timestamp(), current_timestamp() + INTERVAL 24 HOURS, 'CANCELLED', current_timestamp(), current_timestamp());

INSERT OVERWRITE workspace.default.ambulance_dispatches VALUES
  ('amb_001','txn_001','5603','KL-AMB-08','pat_kl_001', 9.9312, 76.2673, 9.9678, 76.2812, current_timestamp(), current_timestamp() + INTERVAL 18 MINUTES, 'EN_ROUTE', current_timestamp(), current_timestamp()),
  ('amb_002','txn_002','2672','DL-AMB-01','pat_dl_001', 28.6139, 77.2090, 28.6500, 77.2200, current_timestamp(), current_timestamp() + INTERVAL 25 MINUTES, 'EN_ROUTE', current_timestamp(), current_timestamp()),
  ('amb_003','txn_003','186', 'GJ-AMB-02','pat_gj_001', 23.0225, 72.5714, 23.0500, 72.6000, current_timestamp(), current_timestamp() + INTERVAL 12 MINUTES, 'ARRIVED', current_timestamp(), current_timestamp()),
  ('amb_004','txn_004','959', 'UP-AMB-04','pat_up_001', 29.4544, 77.3088, 29.5000, 77.3200, current_timestamp(), current_timestamp() + INTERVAL 35 MINUTES, 'DISPATCHED', current_timestamp(), current_timestamp()),
  ('amb_005','txn_005','881', 'OD-AMB-06','pat_od_001', 20.4625, 85.8828, 20.5000, 85.9000, current_timestamp(), current_timestamp() + INTERVAL 22 MINUTES, 'EN_ROUTE', current_timestamp(), current_timestamp());

INSERT OVERWRITE workspace.default.doctor_slots VALUES
  ('slot_001','txn_001','5603','dr_n_menon','Cardiology','pat_kl_001', current_timestamp() + INTERVAL 30 MINUTES, current_timestamp() + INTERVAL 90 MINUTES, 'CONFIRMED', current_timestamp(), current_timestamp()),
  ('slot_002','txn_002','2672','dr_arvind_kapoor','Hepatology','pat_dl_001', current_timestamp() + INTERVAL 45 MINUTES, current_timestamp() + INTERVAL 165 MINUTES, 'CONFIRMED', current_timestamp(), current_timestamp()),
  ('slot_003','txn_003','186', 'dr_kavita_shah','Ophthalmology','pat_gj_001', current_timestamp() + INTERVAL 20 MINUTES, current_timestamp() + INTERVAL 80 MINUTES, 'CONFIRMED', current_timestamp(), current_timestamp()),
  ('slot_004','txn_004','959', 'dr_rajesh_yadav','Emergency Medicine','pat_up_001', current_timestamp() + INTERVAL 40 MINUTES, current_timestamp() + INTERVAL 100 MINUTES, 'IN_PROGRESS', current_timestamp(), current_timestamp()),
  ('slot_005','txn_005','881', 'dr_pratap_panda','Ophthalmology','pat_od_001', current_timestamp() + INTERVAL 25 MINUTES, current_timestamp() + INTERVAL 70 MINUTES, 'CONFIRMED', current_timestamp(), current_timestamp());

INSERT OVERWRITE workspace.default.drug_reservations VALUES
  ('drug_001','txn_001','5603','C01EB17','Ivabradine', 5.0, 'mg', 'pat_kl_001', 'RESERVED', current_timestamp(), current_timestamp()),
  ('drug_002','txn_002','2672','J01CR02','Co-amoxiclav', 1.0, 'g', 'pat_dl_001', 'DISPENSED', current_timestamp(), current_timestamp()),
  ('drug_003','txn_003','186','S01ED01','Timolol', 0.25, 'percent', 'pat_gj_001', 'DISPENSED', current_timestamp(), current_timestamp()),
  ('drug_004','txn_004','959','N02BE01','Paracetamol IV', 1.0, 'g', 'pat_up_001', 'RESERVED', current_timestamp(), current_timestamp()),
  ('drug_005','txn_005','881','S01ED01','Timolol', 0.25, 'percent', 'pat_od_001', 'DISPENSED', current_timestamp(), current_timestamp());

-- 20 outcomes:
--   arc A — INHS Sanjivani (5603) gets 6 positive → reputation 1.0 → trust holds (cap doesn't fire because reputation ≥ trust)
--   arc B — Aradhna (959) gets 6 outcomes mostly negative → reputation ~0.33 → trust caps DOWN from 0.831 to ~0.43 (visible calibration!)
--   plus 2 each for 2672, 186, 881 (below 5-outcome threshold, shown as "n=2 — not enough data" in UI)
INSERT OVERWRITE workspace.default.outcome_feedback VALUES
  -- arc A: INHS Sanjivani — system confirms LLM was right
  ('fb_001','txn_001','pat_kl_001','5603','bed',         1.0, 0.95, 'sms',        'admitted to ICU on arrival, no wait', current_timestamp()),
  ('fb_002','txn_001','pat_kl_001','5603','oxygen',      1.0, 0.95, 'sms',        'oxygen pipeline working', current_timestamp()),
  ('fb_003','txn_001','pat_kl_001','5603','specialist',  1.0, 0.90, 'voice',      'cardiologist on duty as expected', current_timestamp()),
  ('fb_004','txn_001','pat_kl_001','5603','drug',        1.0, 0.90, 'sms',        'cardiac drugs available', current_timestamp()),
  ('fb_005',NULL,     'pat_kl_002','5603','bed',         1.0, 0.95, 'ngo_visit',  'NGO confirmed bed availability week prior', current_timestamp()),
  ('fb_006',NULL,     'pat_kl_003','5603','specialist',  1.0, 0.90, 'ngo_visit',  'cardiologist confirmed in roster', current_timestamp()),
  -- arc B: Aradhna — outcomes contradict optimistic LLM, calibration caps trust DOWN
  ('fb_007','txn_004','pat_up_001','959', 'bed',         0.0, 0.80, 'voice',      'no ICU bed, shifted to nearby facility', current_timestamp()),
  ('fb_008','txn_004','pat_up_001','959', 'oxygen',      0.5, 0.75, 'nurse_note', 'portable cylinder only, no pipeline', current_timestamp()),
  ('fb_009','txn_004','pat_up_001','959', 'specialist',  0.0, 0.85, 'voice',      'emergency physician on leave, junior doctor only', current_timestamp()),
  ('fb_010','txn_004','pat_up_001','959', 'drug',        0.5, 0.80, 'sms',        'paracetamol available, IV route was missing', current_timestamp()),
  ('fb_011',NULL,     'pat_up_002','959', 'bed',         0.0, 0.80, 'ngo_visit',  'NGO inspection found 0/8 ICU beds available, all occupied', current_timestamp()),
  ('fb_012',NULL,     'pat_up_003','959', 'specialist',  0.0, 0.85, 'ngo_visit',  'NGO follow-up: trauma surgeon position vacant 2 months', current_timestamp()),
  -- 2 outcomes each for 2672, 186, 881 (below threshold, demonstrates "n_outcomes < 5 → use llm trust as-is")
  ('fb_013','txn_002','pat_dl_001','2672','bed',         1.0, 0.90, 'sms',        'liver suite ready as scheduled', current_timestamp()),
  ('fb_014','txn_002','pat_dl_001','2672','specialist',  1.0, 0.90, 'voice',      'hepatologist visit completed', current_timestamp()),
  ('fb_015','txn_003','pat_gj_001','186', 'specialist',  1.0, 0.85, 'sms',        'ophthalmologist available', current_timestamp()),
  ('fb_016','txn_003','pat_gj_001','186', 'drug',        1.0, 0.85, 'sms',        'eye drops dispensed', current_timestamp()),
  ('fb_017','txn_005','pat_od_001','881', 'specialist',  1.0, 0.85, 'sms',        'ophthalmologist seen on time', current_timestamp()),
  ('fb_018','txn_005','pat_od_001','881', 'drug',        0.0, 0.80, 'ngo_visit',  'eye drops out of stock, redirected to nearby pharmacy', current_timestamp());
