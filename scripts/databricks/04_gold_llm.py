#!/usr/bin/env python3
"""Load LLM trust artifact (256 hospitals × Llama 3.3 70B) into gold_trust_llm.

Source: data/llm_artifacts/trust_results_llama_3_3_70b.jsonl  (committed in repo)
Target: workspace.default.gold_trust_llm

Re-uses the parquet → UC Volume → CREATE TABLE pattern from 00_bronze_ingest.py.
"""
import json, os, subprocess, sys
from pathlib import Path
import pandas as pd

PROFILE = os.environ.get("DBX_PROFILE", "tero2")
WH = os.environ.get("DBX_WH", "10fff96dd6d936b5")
MODEL = "databricks-meta-llama-3-3-70b-instruct"
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SRC = REPO_ROOT / "data" / "llm_artifacts" / "trust_results_llama_3_3_70b.jsonl"
LOCAL_PARQUET = "/tmp/gold_trust_llm.parquet"
VOLUME_PATH = "/Volumes/workspace/default/raw/gold_trust_llm.parquet"
TABLE = "workspace.default.gold_trust_llm"

def sql(stmt):
    payload = json.dumps({"statement": stmt, "warehouse_id": WH, "wait_timeout": "50s"})
    r = subprocess.run(["databricks","api","post","-p",PROFILE,"/api/2.0/sql/statements","--json",payload],
                       capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(r.stderr or r.stdout)
    d = json.loads(r.stdout)
    if d.get("status",{}).get("state") == "FAILED":
        sys.exit(d["status"].get("error",{}).get("message"))
    return d

# 1. flatten JSONL to parquet
rows = []
with open(SRC) as f:
    for line in f:
        r = json.loads(line)
        if "_error" in r["result"]:
            continue
        res = r["result"]
        # clamp probability fields to [0,1] — defends against LLM returning 1.5/-0.2 etc.
        clip = lambda v: max(0.0, min(1.0, float(v)))
        rows.append({
            "facility_id":   str(r["facility_id"]),
            "name":          r["name"],
            "p_bed":         clip(res.get("p_bed", 0)),
            "p_oxygen":      clip(res.get("p_oxygen", 0)),
            "p_drug":        clip(res.get("p_drug", 0)),
            "p_specialist":  clip(res.get("p_specialist", 0)),
            "ci":            clip(res.get("ci", 0)),
            "reasoning":     res.get("reasoning", ""),
            "tokens":        int(r.get("tokens", 0)),
            "model_endpoint": MODEL,
        })

df = pd.DataFrame(rows)
df.to_parquet(LOCAL_PARQUET, index=False)
print(f"flattened {len(df)} rows → {LOCAL_PARQUET}")

# 2. upload to UC Volume
subprocess.run(["databricks","fs","cp",LOCAL_PARQUET,f"dbfs:{VOLUME_PATH}","-p",PROFILE,"--overwrite"], check=True)

# 3. create table
sql(f"CREATE OR REPLACE TABLE {TABLE} AS SELECT * FROM parquet.`{VOLUME_PATH}`")
n = sql(f"SELECT COUNT(*) AS n FROM {TABLE}")["result"]["data_array"][0][0]
print(f"✓ {TABLE} created with {n} rows")

# 4. quick distribution
dist = sql(f"""SELECT
  ROUND(AVG(p_bed),2) AS p_bed_avg,
  ROUND(AVG(p_oxygen),2) AS p_oxygen_avg,
  ROUND(AVG(p_drug),2) AS p_drug_avg,
  ROUND(AVG(p_specialist),2) AS p_specialist_avg,
  ROUND(AVG((p_bed+p_oxygen+p_drug+p_specialist)/4.0),2) AS llm_trust_avg
FROM {TABLE}""")
cols = [c["name"] for c in dist["manifest"]["schema"]["columns"]]
vals = dist["result"]["data_array"][0]
print(dict(zip(cols, vals)))
