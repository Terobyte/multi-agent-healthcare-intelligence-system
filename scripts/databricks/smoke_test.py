#!/usr/bin/env python3
"""End-to-end smoke test — runs all 7 demo queries and prints output suitable for the judge demo.

Use during dry-run rehearsal: confirms data layer is healthy and the demo lines hold.
Run: python3 scripts/databricks/smoke_test.py
"""
import json, os, subprocess, sys, time

WH = os.environ.get("DBX_WH", "10fff96dd6d936b5")
PROFILE = os.environ.get("DBX_PROFILE", "tero2")

def q(name, sql):
    print(f"\n\033[1;36m▸ {name}\033[0m")
    print(f"  {sql}")
    payload = json.dumps({"statement": sql, "warehouse_id": WH, "wait_timeout": "50s"})
    r = subprocess.run(["databricks","api","post","-p",PROFILE,"/api/2.0/sql/statements","--json",payload],
                       capture_output=True, text=True)
    d = json.loads(r.stdout)
    if d.get("status",{}).get("state") == "FAILED":
        print(f"  \033[1;31mFAILED:\033[0m {d['status'].get('error',{}).get('message')}")
        return
    if "result" in d and "data_array" in d["result"]:
        cols = [c["name"] for c in d["manifest"]["schema"]["columns"]]
        rows = d["result"]["data_array"]
        widths = [max(len(c), max((len(str(row[i])) for row in rows), default=0)) for i, c in enumerate(cols)]
        print()
        print("  " + "  ".join(c.ljust(widths[i]) for i, c in enumerate(cols)))
        print("  " + "  ".join("─" * widths[i] for i in range(len(cols))))
        for row in rows:
            print("  " + "  ".join(str(v if v is not None else "—").ljust(widths[i]) for i, v in enumerate(row)))
        print(f"\n  \033[2m[{len(rows)} rows]\033[0m")

t0 = time.time()
print("\033[1mDatabricks Healthcare — End-to-End Smoke Test\033[0m")
print(f"workspace: dbc-17e9d40d-5056  profile: {PROFILE}  warehouse: {WH}")

q("1. Top 5 LLM-verified hospitals (full hybrid trust, post two-model)",
  """SELECT name, city, state, ROUND(trust_score,3) AS trust, trust_source, ROUND(max_factor_disagreement,2) AS disagr
     FROM workspace.default.gold_trust_final
     WHERE trust_source IN ('two-model-verified','models-disagree')
     ORDER BY trust_score DESC LIMIT 5""")

q("2. Trust source distribution (the 4-tier badge story)",
  """SELECT trust_source, COUNT(*) AS n, ROUND(AVG(trust_score),3) AS avg_trust
     FROM workspace.default.gold_trust_final
     GROUP BY trust_source ORDER BY n DESC""")

q("3. NGO Desert headlines — Bihar + Maharashtra",
  """SELECT state, COUNT(*) AS pins, SUM(n_facilities) AS facilities,
            SUM(CASE WHEN n_oncology=0 THEN 1 ELSE 0 END) AS zero_oncology,
            SUM(CASE WHEN n_emergency=0 THEN 1 ELSE 0 END) AS zero_emergency
     FROM workspace.default.gold_pin_capabilities
     WHERE state IN ('Bihar','Maharashtra','Kerala','Uttar Pradesh')
     GROUP BY state ORDER BY pins DESC""")

q("4. Atomic Booking — 5 successful 4-way bookings",
  """SELECT transaction_id, patient_id, bed_id, doctor_specialty, drug_name
     FROM workspace.default.v_committed_bookings
     ORDER BY transaction_id""")

q("5. Saga rollback — txn_999 ambulance unavailable",
  """SELECT transaction_id, status, failure_reason FROM workspace.default.txn_atomic
     WHERE status = 'ROLLED_BACK'""")

q("6. Outcome learning loop — INHS Sanjivani 6 outcomes",
  """SELECT facility_id, name, trust_source, ROUND(trust_raw,3) AS trust_raw,
            total_outcomes, ROUND(reputation_score,3) AS rep, ROUND(trust_calibrated,3) AS calibrated
     FROM workspace.default.v_trust_calibrated
     WHERE total_outcomes > 0 ORDER BY total_outcomes DESC""")

q("7. Models disagree case — where validator caught uncertainty",
  """SELECT s.name, s.city, s.state,
            ROUND(t.v1_p_bed,2) AS v1_bed, ROUND(t.v2_p_bed,2) AS v2_bed,
            ROUND(t.v1_p_oxygen,2) AS v1_o2, ROUND(t.v2_p_oxygen,2) AS v2_o2,
            ROUND(t.max_factor_disagreement,2) AS max_disagr
     FROM workspace.default.gold_trust_two_model t
     JOIN workspace.default.silver_facilities s ON s.facility_id = t.facility_id
     WHERE t.verification_status = 'models-disagree'
     ORDER BY t.max_factor_disagreement DESC LIMIT 5""")

print(f"\n\033[1;32m✓ smoke test complete\033[0m  ({time.time()-t0:.1f}s)")
