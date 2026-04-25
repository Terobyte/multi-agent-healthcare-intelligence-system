# Demo Runbook — 5-minute walkthrough

> Use this in dry-run rehearsals. Each step is one SQL query in the Databricks SQL Editor.
> Workspace: https://dbc-17e9d40d-5056.cloud.databricks.com → SQL Editor → paste each block.
> Or run all 7 in one shot: `python3 scripts/databricks/smoke_test.py`.

---

## 0. Setup (30s)

> "We're sitting on top of a Databricks Lakehouse — 10,000 Indian healthcare facilities from the VF dataset, fully ingested, cleaned, scored by two foundation models, and ready for atomic booking."

```sql
SHOW TABLES IN workspace.default;
-- → 14 tables + 3 views
```

---

## 1. The trust layer (60s) — the killer

> "We don't just trust a single LLM. We use Llama 3.3 70B as the Extractor and Llama 4 Maverick as the Validator. When they agree within 0.20 across all 4 factors (bed/oxygen/drug/specialist), we badge the hospital as **two-model-verified**. When they disagree, we **explicitly warn** the user."

```sql
SELECT trust_source, COUNT(*) AS n, ROUND(AVG(trust_score),3) AS avg_trust
FROM workspace.default.gold_trust_final
GROUP BY trust_source ORDER BY n DESC;
```

Expected:
| trust_source | n | avg_trust |
|---|---|---|
| rule-inferred | 9738 | 0.609 |
| models-disagree | 169 | 0.669 |
| two-model-verified | 80 | 0.695 |
| llm-verified | 13 | 0.648 |

Then:

```sql
SELECT name, city, state, ROUND(trust_score,3) AS trust, trust_source, ROUND(max_factor_disagreement,2) AS disagr
FROM workspace.default.gold_trust_final
WHERE trust_source = 'two-model-verified'
ORDER BY trust_score DESC LIMIT 5;
```

> "INHS Sanjivani Kochi at trust 0.888 — both models agreed within 0.10."

---

## 2. The disagreement story (45s) — the proof

> "And here's where the validator catches uncertainty — Aadit Eye Hospital: Llama 3.3 said 'high probability of bed' (0.8), Maverick said 'no evidence' (0.0). Max disagreement 0.8. We don't bury this — we surface it as 'requires human review'."

```sql
SELECT s.name, s.city, s.state,
       ROUND(t.v1_p_bed,2) AS llama3_bed, ROUND(t.v2_p_bed,2) AS llama4_bed,
       ROUND(t.max_factor_disagreement,2) AS max_disagr
FROM workspace.default.gold_trust_two_model t
JOIN workspace.default.silver_facilities s ON s.facility_id = t.facility_id
WHERE t.verification_status = 'models-disagree'
ORDER BY t.max_factor_disagreement DESC LIMIT 5;
```

---

## 3. NGO Desert Map (45s) — the social impact angle

> "Here's why this matters. India has 4,964 PIN codes covered by our dataset. Bihar has 421 facilities — but **149 of its 153 PIN codes have ZERO oncology**. 130 have zero emergency medicine. We give every NGO a heatmap of where the next clinic should go."

```sql
SELECT state, COUNT(*) AS pins, SUM(n_facilities) AS facilities,
       SUM(CASE WHEN n_oncology=0 THEN 1 ELSE 0 END) AS zero_oncology,
       SUM(CASE WHEN n_emergency=0 THEN 1 ELSE 0 END) AS zero_emergency
FROM workspace.default.gold_pin_capabilities
WHERE state IN ('Bihar','Maharashtra','Kerala','Uttar Pradesh','Tamil Nadu')
GROUP BY state ORDER BY zero_oncology DESC;
```

---

## 4. Atomic Booking (60s) — the engineering depth

> "When a patient says 'book me INHS Sanjivani', that's actually 4 reservations in one transaction: bed + ambulance + doctor slot + drug. If any one fails, all four roll back atomically. Real Delta tables, real ACID. Here are 5 successful bookings:"

```sql
SELECT transaction_id, patient_id, bed_id, doctor_specialty, drug_name
FROM workspace.default.v_committed_bookings
ORDER BY transaction_id;
```

> "And here's a rollback case — txn_999 ambulance unavailable. The view filters it out automatically. No half-booked patient with a bed but no transport."

```sql
SELECT transaction_id, status, failure_reason
FROM workspace.default.txn_atomic
WHERE status = 'ROLLED_BACK';
```

---

## 5. Outcome Learning Loop (60s) — the calibration

> "After each booking, we ping the patient at T+2h: was the bed actually there? Was the specialist on duty? Those outcomes feed back into a per-hospital reputation score. INHS Sanjivani has 6 outcomes, all positive — reputation 1.0 — its trust holds at 0.888. If reputation dropped below trust, we'd cap it. The system gets smarter every visit."

```sql
SELECT facility_id, name, trust_source, ROUND(trust_raw,3) AS trust_raw,
       total_outcomes, ROUND(reputation_score,3) AS rep, ROUND(trust_calibrated,3) AS calibrated
FROM workspace.default.v_trust_calibrated
WHERE total_outcomes > 0
ORDER BY total_outcomes DESC;
```

---

## 6. Vector Search retrieval (45s) — the RAG plumbing

> "Behind the scenes, we have a Mosaic AI Vector Search Delta-sync index over all 10,000 facility profiles using BGE-large embeddings. The TriageAgent uses it to map symptoms → relevant facilities."

(While VS provisions, fall back to:)

```sql
SELECT name, city, state, ROUND(trust_score,3) AS trust
FROM workspace.default.gold_trust_final
WHERE array_contains(specialties, 'cardiology')
  AND state = 'Bihar'
  AND trust_score >= 0.6
ORDER BY trust_score DESC LIMIT 5;
```

> "Once the index finishes provisioning, this becomes a semantic query — patient says 'chest pain' and we pull cardiac-capable facilities ranked by trust × distance."

---

## 7. Closing (30s)

> "So in summary: we have **80 hospitals two-model-verified**, **169 flagged for human review**, **5 atomic bookings completed**, **14 patient outcome pings**, and a **NGO desert map covering 3,736 PIN codes**. All of it on Databricks — Delta tables, Foundation Model APIs, Vector Search, all native. Reproducible from scratch in 5 minutes via `scripts/databricks/00→10`."

---

## Backup talking points (if asked)

- **"How do you avoid hallucination?"** → Two-model verification. If Llama 3.3 and Llama 4 Maverick disagree on a factor by >0.20, we flag the hospital as low-confidence rather than blending.
- **"What happens when a hospital changes capacity?"** → Outcome feedback table is append-only, fed by patient pings (SMS/voice/NGO-visit). v_trust_calibrated re-runs on every read; no batch lag.
- **"How do you handle missing data?"** → Hybrid approach. 256 hospitals get LLM scoring (rich descriptions), 9744 get rule-based proxies (4 per-factor heuristics). Every score is annotated with source so the UI shows "verified" vs "inferred".
- **"What if your LLM endpoint is down?"** → Fallback to rule-based scores. trust_source column tells UI which to display.
- **"Cost?"** → Two-model run on 256 hospitals = ~$0.60 in tokens (Llama 3.3 + Llama 4 Maverick combined). Trial $400 credit, ~99.85% remaining.
- **"Why Databricks?"** → Foundation Model APIs (Llama + GPT-5.x intra-platform, no egress), Delta ACID for booking, Vector Search Delta-sync (no separate index pipeline), Unity Catalog governance (PII handling for patient_id hashes).
