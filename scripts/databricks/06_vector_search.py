#!/usr/bin/env python3
"""Vector Search: build retrieval index over silver_facilities text.

Pipeline:
  1. Build workspace.default.silver_facilities_text (facility_id PK + doc_text)
     - doc_text = name + city/state + description + specialties + capabilities + procedures
     - delta.enableChangeDataFeed = true (required for Delta-sync index)
  2. Create vector-search endpoint `vs_healthcare` (1 endpoint allowed on Trial)
  3. Create Delta-sync index over silver_facilities_text using databricks-bge-large-en
  4. Poll for READY then run smoke-test queries.

Used by:
  - TriageAgent (symptom → relevant specialty/facility match)
  - Validator (similar past cases / reasoning anchor)
"""
import json, os, subprocess, sys, time
from pathlib import Path

PROFILE = os.environ.get("DBX_PROFILE", "tero2")
WH = os.environ.get("DBX_WH", "10fff96dd6d936b5")
ENDPOINT = "vs_healthcare"
SOURCE_TABLE = "workspace.default.silver_facilities_text"
INDEX_NAME = "workspace.default.silver_facilities_text_idx"
EMBED_MODEL = "databricks-bge-large-en"

def sh(cmd, check=True):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if check and r.returncode != 0:
        print(r.stderr or r.stdout, file=sys.stderr)
        sys.exit(r.returncode)
    return r.stdout

def sql(stmt):
    payload = json.dumps({"statement": stmt, "warehouse_id": WH, "wait_timeout": "50s"})
    out = sh(["databricks","api","post","-p",PROFILE,"/api/2.0/sql/statements","--json",payload])
    d = json.loads(out)
    state = d.get("status",{}).get("state")
    if state == "FAILED":
        sys.exit(d["status"].get("error",{}).get("message"))
    return d

def api(method, path, body=None):
    cmd = ["databricks","api",method,"-p",PROFILE,path]
    if body is not None:
        cmd += ["--json", json.dumps(body)]
    out = sh(cmd, check=False)
    if not out.strip():
        return {}
    return json.loads(out)

# 1. build silver_facilities_text with PK + CDF
print("→ building silver_facilities_text...")
sql(f"""
CREATE OR REPLACE TABLE {SOURCE_TABLE} (
  facility_id STRING NOT NULL,
  name STRING,
  city STRING,
  state STRING,
  facility_type STRING,
  doc_text STRING,
  CONSTRAINT silver_text_pk PRIMARY KEY (facility_id)
) TBLPROPERTIES (delta.enableChangeDataFeed = true)
""")
sql(f"""
INSERT INTO {SOURCE_TABLE}
SELECT
  facility_id, name, city, state, facility_type,
  concat_ws(' \\n ',
    concat('Facility: ', coalesce(name,'')),
    concat('Type: ', coalesce(facility_type,'')),
    concat('Location: ', coalesce(city,''), ', ', coalesce(state,'')),
    concat('Description: ', coalesce(description,'')),
    concat('Specialties: ', coalesce(array_join(specialties, ', '), '')),
    concat('Procedures: ',  coalesce(array_join(procedures,  ', '), '')),
    concat('Capabilities: ',coalesce(array_join(capabilities,', '), '')),
    concat('Equipment: ',   coalesce(array_join(equipment,   ', '), ''))
  ) AS doc_text
FROM workspace.default.silver_facilities
""")
n = sql(f"SELECT COUNT(*) FROM {SOURCE_TABLE}")["result"]["data_array"][0][0]
print(f"  ✓ {SOURCE_TABLE} populated with {n} rows")

# 2. create vector search endpoint (idempotent)
print(f"\n→ creating endpoint {ENDPOINT}...")
existing = api("get","/api/2.0/vector-search/endpoints").get("endpoints",[])
if any(e.get("name") == ENDPOINT for e in existing):
    print(f"  endpoint {ENDPOINT} already exists")
else:
    r = api("post","/api/2.0/vector-search/endpoints",
            {"name": ENDPOINT, "endpoint_type": "STANDARD"})
    print(f"  create response: {r.get('endpoint_status', r)}")

# 3. wait for endpoint READY
print("→ polling endpoint state (may take 5-10 min)...")
for i in range(60):
    e = api("get", f"/api/2.0/vector-search/endpoints/{ENDPOINT}")
    state = e.get("endpoint_status",{}).get("state","?")
    print(f"  [{i*15}s] state={state}")
    if state == "ONLINE":
        break
    if state in ("OFFLINE","FAILED"):
        sys.exit(f"endpoint went {state}: {e}")
    time.sleep(15)
else:
    sys.exit("endpoint did not become ONLINE within 15 min")

# 4. create Delta-sync index
print(f"\n→ creating index {INDEX_NAME}...")
existing_idx = api("get", f"/api/2.0/vector-search/endpoints/{ENDPOINT}/indexes").get("vector_indexes",[])
if any(i.get("name") == INDEX_NAME for i in existing_idx):
    print(f"  index {INDEX_NAME} already exists")
else:
    r = api("post","/api/2.0/vector-search/indexes", {
        "name": INDEX_NAME,
        "endpoint_name": ENDPOINT,
        "primary_key": "facility_id",
        "index_type": "DELTA_SYNC",
        "delta_sync_index_spec": {
            "source_table": SOURCE_TABLE,
            "pipeline_type": "TRIGGERED",
            "embedding_source_columns": [{
                "name": "doc_text",
                "embedding_model_endpoint_name": EMBED_MODEL
            }]
        }
    })
    print(f"  create response: {r.get('status', r)}")

# 5. wait for index READY
print("→ polling index sync state (may take 5-15 min for 10k rows)...")
for i in range(80):
    idx = api("get", f"/api/2.0/vector-search/indexes/{INDEX_NAME}")
    state = idx.get("status",{}).get("detailed_state","?")
    indexed = idx.get("status",{}).get("indexed_row_count",0)
    print(f"  [{i*15}s] state={state}  indexed={indexed}")
    if state in ("ONLINE","ONLINE_NO_PENDING_UPDATE"):
        break
    if "FAILED" in state:
        sys.exit(f"index {state}: {idx}")
    time.sleep(15)
else:
    sys.exit("index did not become ONLINE within 20 min")

# 6. smoke test
print("\n→ smoke-test queries:")
for q in ["chest pain emergency cardiology hospital",
         "child vaccination paediatric clinic",
         "kidney dialysis nephrology"]:
    r = api("post", f"/api/2.0/vector-search/indexes/{INDEX_NAME}/query",
            {"query_text": q, "columns": ["facility_id","name","city","state","facility_type"], "num_results": 3})
    rows = r.get("result",{}).get("data_array",[])
    print(f"\n  query: {q}")
    for row in rows:
        print(f"    {row}")
print("\n✓ Vector Search ready")
