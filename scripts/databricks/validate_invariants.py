#!/usr/bin/env python3
"""Invariant validator: fails LOUDLY if any data layer drifted from spec.

Run after every pipeline rerun and before every demo dry-run. Exits non-zero on any drift.

Checks:
  1. row counts per table     (silver=10000, llm_v1=256, llm_v2=255, two_model=262, final=10000)
  2. score ranges in [0, 1]   (trust_score, p_bed/p_oxygen/p_drug/p_specialist, reputation_score)
  3. badge distribution       (two-model-verified=139, models-disagree=110, llm=13, rule=9738)
  4. demo arc anchors         (5603=0.888, 959=0.831/calibrated 0.35, 186=0.425, 2672=0.863, 881=0.825)
  5. reputation aggregation   (5603 rep=1.0, 959 rep=0.25)
  6. saga integrity           (v_committed_bookings: 5 rows, 0 partial commits, txn_999 excluded)
  7. desert headlines         (Bihar 149 zero-onc PINs, Maharashtra 403)
"""
import json, os, subprocess, sys

PROFILE = os.environ.get("DBX_PROFILE", "tero2")
WH = os.environ.get("DBX_WH", "10fff96dd6d936b5")
GREEN = "\033[1;32m"; RED = "\033[1;31m"; DIM = "\033[2m"; END = "\033[0m"

def sql(stmt):
    payload = json.dumps({"statement": stmt, "warehouse_id": WH, "wait_timeout": "50s"})
    r = subprocess.run(["databricks","api","post","-p",PROFILE,"/api/2.0/sql/statements","--json",payload],
                       capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        sys.exit(f"CLI error: {r.stderr or r.stdout}")
    d = json.loads(r.stdout)
    if d.get("status",{}).get("state") == "FAILED":
        sys.exit(f"SQL FAILED: {d['status'].get('error',{}).get('message')}")
    return d["result"]["data_array"]

failures = []
checks = 0

def check(label, query, expected, tolerance=0):
    """Run query, expect single scalar (or first cell of first row). Compare with tolerance."""
    global checks; checks += 1
    rows = sql(query)
    actual = rows[0][0] if rows and rows[0] else None
    # numeric tolerance match
    try:
        if abs(float(actual) - float(expected)) <= tolerance:
            print(f"  {GREEN}✓{END} {label}: {actual}")
            return
    except (TypeError, ValueError):
        if str(actual) == str(expected):
            print(f"  {GREEN}✓{END} {label}: {actual}")
            return
    print(f"  {RED}✗{END} {label}: expected {expected}, got {actual}")
    failures.append((label, expected, actual))

print(f"{DIM}validate_invariants — workspace: {PROFILE}{END}\n")

print("[1] row counts")
check("silver_facilities = 10000",     "SELECT COUNT(*) FROM workspace.default.silver_facilities",     10000)
check("gold_trust_rules = 10000",      "SELECT COUNT(*) FROM workspace.default.gold_trust_rules",      10000)
check("gold_trust_llm = 256",          "SELECT COUNT(*) FROM workspace.default.gold_trust_llm",        256)
check("gold_trust_llm_v2 = 255",       "SELECT COUNT(*) FROM workspace.default.gold_trust_llm_v2",     255)
check("gold_trust_two_model = 262",    "SELECT COUNT(*) FROM workspace.default.gold_trust_two_model",  262)
check("gold_trust_final = 10000",      "SELECT COUNT(*) FROM workspace.default.gold_trust_final",      10000)
check("outcome_feedback = 18",         "SELECT COUNT(*) FROM workspace.default.outcome_feedback",      18)
check("txn_atomic = 6",                "SELECT COUNT(*) FROM workspace.default.txn_atomic",            6)
check("v_committed_bookings = 5",      "SELECT COUNT(*) FROM workspace.default.v_committed_bookings",  5)

print("\n[2] score ranges in [0, 1]")
check("trust_score never < 0",         "SELECT COUNT(*) FROM workspace.default.gold_trust_final WHERE trust_score < 0", 0)
check("trust_score never > 1",         "SELECT COUNT(*) FROM workspace.default.gold_trust_final WHERE trust_score > 1", 0)
check("p_bed never out of range",      "SELECT COUNT(*) FROM workspace.default.gold_trust_final WHERE p_bed < 0 OR p_bed > 1", 0)
check("p_oxygen never out of range",   "SELECT COUNT(*) FROM workspace.default.gold_trust_final WHERE p_oxygen < 0 OR p_oxygen > 1", 0)
check("p_drug never out of range",     "SELECT COUNT(*) FROM workspace.default.gold_trust_final WHERE p_drug < 0 OR p_drug > 1", 0)
check("p_specialist never out of range","SELECT COUNT(*) FROM workspace.default.gold_trust_final WHERE p_specialist < 0 OR p_specialist > 1", 0)
check("reputation_score never out",    "SELECT COUNT(*) FROM workspace.default.v_agent_reputation WHERE reputation_score < 0 OR reputation_score > 1", 0)
check("trust_calibrated never out",    "SELECT COUNT(*) FROM workspace.default.v_trust_calibrated WHERE trust_calibrated < 0 OR trust_calibrated > 1", 0)
check("no NULL trust_score",           "SELECT COUNT(*) FROM workspace.default.gold_trust_final WHERE trust_score IS NULL", 0)

print("\n[3] badge distribution")
check("two-model-verified = 139",      "SELECT COUNT(*) FROM workspace.default.gold_trust_final WHERE trust_source='two-model-verified'", 139)
check("models-disagree = 110",         "SELECT COUNT(*) FROM workspace.default.gold_trust_final WHERE trust_source='models-disagree'", 110)
check("llm-verified = 13",             "SELECT COUNT(*) FROM workspace.default.gold_trust_final WHERE trust_source='llm-verified'", 13)
check("rule-inferred = 9738",          "SELECT COUNT(*) FROM workspace.default.gold_trust_final WHERE trust_source='rule-inferred'", 9738)

print("\n[4] demo arc anchor values")
check("5603 INHS Sanjivani trust 0.888",  "SELECT ROUND(trust_score,3) FROM workspace.default.gold_trust_final WHERE facility_id='5603'", 0.888, tolerance=0.001)
check("5603 calibrated stays 0.888",      "SELECT ROUND(trust_calibrated,3) FROM workspace.default.v_trust_calibrated WHERE facility_id='5603'", 0.888, tolerance=0.001)
check("959 Aradhna trust_raw 0.831",      "SELECT ROUND(trust_score,3) FROM workspace.default.gold_trust_final WHERE facility_id='959'", 0.831, tolerance=0.001)
check("959 calibrated drops to 0.35",     "SELECT ROUND(trust_calibrated,3) FROM workspace.default.v_trust_calibrated WHERE facility_id='959'", 0.35, tolerance=0.001)
check("186 Aadit Eye trust 0.425",        "SELECT ROUND(trust_score,3) FROM workspace.default.gold_trust_final WHERE facility_id='186'", 0.425, tolerance=0.001)
check("186 max_disagr = 0.8",             "SELECT ROUND(max_factor_disagreement,2) FROM workspace.default.gold_trust_final WHERE facility_id='186'", 0.8, tolerance=0.001)
check("2672 Delhi Liver trust 0.863",     "SELECT ROUND(trust_score,3) FROM workspace.default.gold_trust_final WHERE facility_id='2672'", 0.863, tolerance=0.001)
check("881 Apex Eye trust 0.825",         "SELECT ROUND(trust_score,3) FROM workspace.default.gold_trust_final WHERE facility_id='881'", 0.825, tolerance=0.001)

print("\n[5] reputation aggregation (per-factor equal weight)")
check("5603 reputation = 1.0",         "SELECT reputation_score FROM workspace.default.v_agent_reputation WHERE facility_id='5603'", 1.0, tolerance=0.001)
check("959 reputation = 0.25",         "SELECT reputation_score FROM workspace.default.v_agent_reputation WHERE facility_id='959'", 0.25, tolerance=0.001)

print("\n[6] saga integrity")
check("v_committed_bookings = 5 rows", "SELECT COUNT(*) FROM workspace.default.v_committed_bookings", 5)
check("0 partial-commit nulls",
      """SELECT COUNT(*) FROM workspace.default.v_committed_bookings
         WHERE bed_reservation_id IS NULL OR dispatch_id IS NULL OR doctor_slot_id IS NULL OR drug_reservation_id IS NULL""", 0)
check("ROLLED_BACK txn_999 excluded",  "SELECT COUNT(*) FROM workspace.default.v_committed_bookings WHERE transaction_id='txn_999'", 0)
check("ROLLED_BACK txn_999 in ledger", "SELECT COUNT(*) FROM workspace.default.txn_atomic WHERE transaction_id='txn_999' AND status='ROLLED_BACK'", 1)

print("\n[7] desert headlines")
check("Bihar zero-oncology PINs = 149","SELECT SUM(CASE WHEN n_oncology=0 THEN 1 ELSE 0 END) FROM workspace.default.gold_pin_capabilities WHERE state='Bihar'", 149)
check("Maharashtra zero-onc PINs = 403","SELECT SUM(CASE WHEN n_oncology=0 THEN 1 ELSE 0 END) FROM workspace.default.gold_pin_capabilities WHERE state='Maharashtra'", 403)
check("Maharashtra facilities = 1492", "SELECT SUM(n_facilities) FROM workspace.default.gold_pin_capabilities WHERE state='Maharashtra'", 1492)

print(f"\n{'='*60}")
if failures:
    print(f"{RED}FAILED {len(failures)}/{checks} invariants{END}")
    for label, exp, act in failures:
        print(f"  - {label}: expected={exp}  got={act}")
    sys.exit(1)
else:
    print(f"{GREEN}✓ all {checks} invariants hold{END}")
