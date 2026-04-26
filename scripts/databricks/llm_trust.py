#!/usr/bin/env python3
"""Run Llama 3.3 70B extraction on 262 rich hospitals. Save results to JSON for Delta upload.
Env vars: DBX_PROFILE, DBX_WH, DBX_ENDPOINT."""
import json, os, subprocess, time, sys, concurrent.futures as cf

WH = os.environ.get("DBX_WH", "10fff96dd6d936b5")
PROFILE = os.environ.get("DBX_PROFILE", "tero2")
ENDPOINT = os.environ.get("DBX_ENDPOINT", "databricks-meta-llama-3-3-70b-instruct")
# output filename derived from endpoint so two-model runs don't overwrite each other
_safe_endpoint = ENDPOINT.replace("databricks-", "").replace("meta-", "").replace(".","_").replace("-","_")
OUT = os.environ.get("DBX_OUT", f"/tmp/trust_results_{_safe_endpoint}.jsonl")

def db_sql(sql):
    payload = json.dumps({"statement": sql, "warehouse_id": WH, "wait_timeout": "50s"})
    r = subprocess.run(["databricks","api","post","-p",PROFILE,"/api/2.0/sql/statements","--json",payload],
                       capture_output=True, text=True, timeout=120)
    # surface CLI failures loudly — silent NULL upstream becomes silent {} downstream
    if r.returncode != 0:
        sys.exit(f"db_sql CLI error (rc={r.returncode}): {(r.stderr or r.stdout or '').strip()[:400]}")
    try:
        d = json.loads(r.stdout)
    except json.JSONDecodeError:
        sys.exit(f"db_sql: non-JSON response: {r.stdout[:400]}")
    if d.get("status",{}).get("state") == "FAILED":
        sys.exit(f"db_sql SQL FAILED: {d['status'].get('error',{}).get('message','?')[:400]}")
    return d

def db_llm(prompt, max_tokens=400):
    payload = json.dumps({
        "messages":[{"role":"user","content":prompt}],
        "max_tokens":max_tokens, "temperature":0.1
    })
    r = subprocess.run(["databricks","api","post","-p",PROFILE,f"/serving-endpoints/{ENDPOINT}/invocations","--json",payload],
                       capture_output=True, text=True, timeout=120)
    # per-call failures are tolerated (caller increments error count + skips row)
    # but we annotate the failure mode so the JSONL post-mortem is actionable
    if r.returncode != 0:
        return f"CLI_ERR rc={r.returncode}: {(r.stderr or '').strip()[:200]}", 0
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
    """Extract JSON from LLM response, handling markdown wrapping. Never raises."""
    try:
        text = (text or "").strip()
        # strip ```json ... ``` or ``` ... ``` wrappers (handles single backtick edge case too)
        if text.startswith("```"):
            parts = text.split("```")
            if len(parts) >= 2:
                text = parts[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.strip()
        if "{" not in text or "}" not in text:
            return {"_error": "no JSON braces in response", "_raw": text[:300]}
        start = text.index("{"); end = text.rindex("}") + 1
        parsed = json.loads(text[start:end])
        # clamp probability fields to [0, 1] — defensive against LLM returning 1.5 / -0.2 / etc.
        for k in ("p_bed", "p_oxygen", "p_drug", "p_specialist", "ci"):
            if k in parsed and isinstance(parsed[k], (int, float)):
                parsed[k] = max(0.0, min(1.0, float(parsed[k])))
        return parsed
    except Exception as e:
        return {"_error": str(e), "_raw": text[:300] if isinstance(text, str) else str(text)[:300]}

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
