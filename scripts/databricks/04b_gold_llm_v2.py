#!/usr/bin/env python3
"""Load second-model LLM trust artifact (Llama 4 Maverick on the same 256 hospitals).

Runs IDENTICAL prompt + flow as 04_gold_llm.py, but with Llama 4 Maverick endpoint.
The two outputs feed gold_trust_two_model (validator pattern: independent error modes).

Source: data/llm_artifacts/trust_results_llama_4_maverick.jsonl
Target: workspace.default.gold_trust_llm_v2
"""
import json, os, subprocess, sys
from pathlib import Path
import pandas as pd

PROFILE = os.environ.get("DBX_PROFILE", "tero2")
WH = os.environ.get("DBX_WH", "10fff96dd6d936b5")
MODEL = "databricks-llama-4-maverick"
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SRC = REPO_ROOT / "data" / "llm_artifacts" / "trust_results_llama_4_maverick.jsonl"
LOCAL_PARQUET = "/tmp/gold_trust_llm_v2.parquet"
VOLUME_PATH = "/Volumes/workspace/default/raw/gold_trust_llm_v2.parquet"
TABLE = "workspace.default.gold_trust_llm_v2"

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

rows = []
with open(SRC) as f:
    for line in f:
        r = json.loads(line)
        if "_error" in r["result"]:
            continue
        res = r["result"]
        rows.append({
            "facility_id":   str(r["facility_id"]),
            "name":          r["name"],
            "p_bed":         float(res.get("p_bed", 0)),
            "p_oxygen":      float(res.get("p_oxygen", 0)),
            "p_drug":        float(res.get("p_drug", 0)),
            "p_specialist":  float(res.get("p_specialist", 0)),
            "ci":            float(res.get("ci", 0)),
            "reasoning":     res.get("reasoning", ""),
            "tokens":        int(r.get("tokens", 0)),
            "model_endpoint": MODEL,
        })

df = pd.DataFrame(rows)
df.to_parquet(LOCAL_PARQUET, index=False)
print(f"flattened {len(df)} rows → {LOCAL_PARQUET}")

subprocess.run(["databricks","fs","cp",LOCAL_PARQUET,f"dbfs:{VOLUME_PATH}","-p",PROFILE,"--overwrite"], check=True)
sql(f"CREATE OR REPLACE TABLE {TABLE} AS SELECT * FROM parquet.`{VOLUME_PATH}`")
n = sql(f"SELECT COUNT(*) FROM {TABLE}")["result"]["data_array"][0][0]
print(f"✓ {TABLE} created with {n} rows")
