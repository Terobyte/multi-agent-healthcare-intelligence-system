#!/usr/bin/env python3
"""Bronze ingest: VF xlsx → parquet → UC Volume → managed Delta table.

Usage: python3 00_bronze_ingest.py
Env vars: DBX_PROFILE (default tero2), DBX_WH (default 10fff96dd6d936b5)
Source: data/VF_Hackathon_Dataset_India_Large.xlsx (4.9 MB, 10000 rows × 41 cols)
Target: workspace.default.vf_hackathon_dataset_india_large
"""
import json, os, subprocess, sys
from pathlib import Path
import pandas as pd

PROFILE = os.environ.get("DBX_PROFILE", "tero2")
WH = os.environ.get("DBX_WH", "10fff96dd6d936b5")
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SRC = REPO_ROOT / "data" / "VF_Hackathon_Dataset_India_Large.xlsx"
LOCAL_PARQUET = "/tmp/vf_bronze.parquet"
VOLUME_PATH = "/Volumes/workspace/default/raw/vf_bronze.parquet"
TABLE = "workspace.default.vf_hackathon_dataset_india_large"

def sh(cmd):
    print(f"$ {' '.join(cmd) if isinstance(cmd, list) else cmd}", flush=True)
    r = subprocess.run(cmd if isinstance(cmd, list) else cmd.split(), capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stderr[:500], file=sys.stderr)
        sys.exit(r.returncode)
    return r.stdout

def sql(stmt):
    payload = json.dumps({"statement": stmt, "warehouse_id": WH, "wait_timeout": "50s"})
    out = sh(["databricks", "api", "post", "-p", PROFILE, "/api/2.0/sql/statements", "--json", payload])
    d = json.loads(out)
    state = d.get("status", {}).get("state")
    if state == "FAILED":
        print("SQL FAILED:", d["status"].get("error", {}).get("message"), file=sys.stderr)
        sys.exit(2)
    return d

# 1. xlsx → parquet (coerce all object cols to str — handles xlsx mixed types)
print(f"Reading {SRC}...")
df = pd.read_excel(SRC, dtype=object)
for c in df.columns:
    if df[c].dtype == object:
        df[c] = df[c].astype(str).replace({"nan": None, "NaT": None})
df.to_parquet(LOCAL_PARQUET, index=False)
print(f"  shape={df.shape}, parquet={os.path.getsize(LOCAL_PARQUET)//1024} KB")

# 2. ensure UC volume exists (idempotent — ignore if already there)
subprocess.run(["databricks", "volumes", "create", "workspace", "default", "raw", "MANAGED", "-p", PROFILE],
               capture_output=True)

# 3. upload parquet
sh(["databricks", "fs", "cp", LOCAL_PARQUET, f"dbfs:{VOLUME_PATH}", "-p", PROFILE, "--overwrite"])

# 4. CREATE TABLE
sql(f"CREATE OR REPLACE TABLE {TABLE} AS SELECT * FROM parquet.`{VOLUME_PATH}`")
d = sql(f"SELECT COUNT(*) AS n FROM {TABLE}")
n = d["result"]["data_array"][0][0]
print(f"\n✓ {TABLE} created with {n} rows")
