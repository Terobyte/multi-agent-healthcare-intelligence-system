#!/usr/bin/env python3
"""Run Llama 3.3 70B extraction on 262 rich hospitals. Save results to JSON for Delta upload."""
import json, subprocess, time, sys, concurrent.futures as cf

WH = "a6cf21f5e91a2176"
ENDPOINT = "databricks-meta-llama-3-3-70b-instruct"
OUT = "/tmp/trust_results.jsonl"

def db_sql(sql):
    payload = json.dumps({"statement": sql, "warehouse_id": WH, "wait_timeout": "30s"})
    r = subprocess.run(["databricks","api","post","/api/2.0/sql/statements","--json",payload],
                       capture_output=True, text=True, timeout=60)
    return json.loads(r.stdout)

def db_llm(prompt, max_tokens=400):
    payload = json.dumps({
        "messages":[{"role":"user","content":prompt}],
        "max_tokens":max_tokens, "temperature":0.1
    })
    r = subprocess.run(["databricks","api","post",f"/serving-endpoints/{ENDPOINT}/invocations","--json",payload],
                       capture_output=True, text=True, timeout=60)
    try:
        d = json.loads(r.stdout)
        if "choices" in d:
            return d["choices"][0]["message"]["content"], d.get("usage",{}).get("total_tokens",0)
        return f"ERROR: {d.get('error',d)}", 0
    except Exception as e:
        return f"PARSE_ERR: {e} | {r.stdout[:200]}", 0

def build_prompt(row):
    fid, name, city, state, ftype, desc, specs, procs, equip, caps, ndoc, cap = row
    return f"""You are a Trust Scorer for Indian healthcare facilities. Given this facility, estimate per-factor probabilities (0.0-1.0) that the listed care is actually deliverable.

Facility: {name}
Type: {ftype}
Location: {city}, {state}
Description: {desc[:300] if desc else 'N/A'}
Specialties: {specs[:300] if specs else '[]'}
Procedures: {procs[:300] if procs else '[]'}
Equipment: {equip[:400] if equip else '[]'}
Capabilities: {caps[:400] if caps else '[]'}
Doctors: {ndoc if ndoc else 'unknown'}
Capacity: {cap if cap else 'unknown'}

Score 4 factors (0-1) with brief reasoning. Return ONLY valid JSON, nothing else:
{{"p_bed": 0.0-1.0, "p_oxygen": 0.0-1.0, "p_drug": 0.0-1.0, "p_specialist": 0.0-1.0, "ci": 0.0-0.3, "reasoning": "<one sentence per factor>"}}"""

def parse_response(text):
    """Extract JSON from LLM response, handling markdown wrapping."""
    text = text.strip()
    # strip ```json ... ``` wrappers
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"): text = text[4:]
    # find { ... }
    try:
        start = text.index("{"); end = text.rindex("}") + 1
        return json.loads(text[start:end])
    except Exception as e:
        return {"_error": str(e), "_raw": text[:300]}

def process(row):
    fid = row[0]
    prompt = build_prompt(row)
    content, tokens = db_llm(prompt)
    parsed = parse_response(content)
    return {"facility_id": fid, "name": row[1], "tokens": tokens, "result": parsed, "raw": content[:500]}

# Pull 262 rich hospitals
print("Pulling 262 rich hospitals...", flush=True)
sql = """SELECT facility_id, name, city, state, facility_type, description,
  raw_specialties_json, raw_procedure_json, raw_equipment_json, raw_capability_json,
  num_doctors, capacity
FROM workspace.default.silver_facilities
WHERE facility_type = 'hospital'
  AND size(equipment) >= 1
  AND size(procedures) >= 1
  AND size(capabilities) >= 1
  AND description IS NOT NULL AND description <> ''
ORDER BY facility_id
LIMIT 262"""
d = db_sql(sql)
rows = d.get("result",{}).get("data_array",[])
print(f"Got {len(rows)} hospitals to score.", flush=True)

# Process in parallel (10 concurrent — Foundation Model APIs handle this)
results = []
total_tokens = 0
errors = 0
t0 = time.time()
with cf.ThreadPoolExecutor(max_workers=10) as ex:
    futures = {ex.submit(process, r): r[0] for r in rows}
    for i, fut in enumerate(cf.as_completed(futures), 1):
        try:
            r = fut.result()
            results.append(r)
            total_tokens += r["tokens"]
            if "_error" in r["result"]:
                errors += 1
            if i % 20 == 0 or i == len(rows):
                elapsed = time.time() - t0
                print(f"  [{i}/{len(rows)}] elapsed {elapsed:.0f}s  tokens {total_tokens:,}  errors {errors}", flush=True)
        except Exception as e:
            errors += 1
            print(f"  futerr: {e}", flush=True)

# Save to JSONL
with open(OUT, "w") as f:
    for r in results:
        f.write(json.dumps(r) + "\n")
print(f"\nDone. Saved {len(results)} results to {OUT}")
print(f"Total tokens: {total_tokens:,}  Errors: {errors}/{len(results)}")
print(f"Time: {time.time()-t0:.1f}s")
