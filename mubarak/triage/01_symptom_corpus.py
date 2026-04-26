#!/usr/bin/env python3
"""Create and populate workspace.default.symptom_corpus.

Requirements for Delta-sync Vector Search:
  - `id` column as primary key (VS primary_key field)
  - delta.enableChangeDataFeed = true (CDF must be ON before index creation)

Pipeline:
  1. Convert corpus JSONL → parquet locally
  2. Upload to UC Volume raw/
  3. CREATE OR REPLACE TABLE symptom_corpus with PK + CDF
  4. INSERT INTO from parquet in Volume
  5. Smoke: SELECT count(*) → must be >= 10

Usage:
  cd healthcare
  python3 mubarak/triage/01_symptom_corpus.py

Env vars: DBX_PROFILE (default tero2), DBX_WH (default 10fff96dd6d936b5)
"""
import atexit, json, os, subprocess, sys, tempfile
from pathlib import Path

import pandas as pd

PROFILE = os.environ.get("DBX_PROFILE", "tero2")
WH = os.environ.get("DBX_WH", "10fff96dd6d936b5")

TABLE = "workspace.default.symptom_corpus"
VOLUME_PATH = "/Volumes/workspace/default/raw/symptom_corpus.parquet"
MUBARAK_ROOT = Path(__file__).resolve().parent.parent   # healthcare/mubarak/
JSONL = MUBARAK_ROOT / "corpus" / "symptoms_to_specialty.jsonl"


# ── helpers ──────────────────────────────────────────────────────────────────

def sh(cmd, check=True):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if check and r.returncode != 0:
        print((r.stderr or r.stdout)[:500], file=sys.stderr)
        sys.exit(r.returncode)
    return r.stdout


def sql(stmt):
    payload = json.dumps({"statement": stmt, "warehouse_id": WH, "wait_timeout": "50s"})
    out = sh(["databricks", "api", "post", "-p", PROFILE,
              "/api/2.0/sql/statements", "--json", payload])
    d = json.loads(out)
    state = d.get("status", {}).get("state")
    if state == "FAILED":
        msg = d["status"].get("error", {}).get("message", "unknown")
        print(f"SQL FAILED: {msg}", file=sys.stderr)
        sys.exit(2)
    return d


# ── 1. JSONL → parquet ────────────────────────────────────────────────────────

print(f"→ reading corpus from {JSONL}...")
rows = []
with open(JSONL) as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        r = json.loads(line)
        rows.append({
            "id":            r["id"],
            "text":          r["text"],
            "specialty":     r["specialty"],
            "urgency":       int(r["urgency"]),
            "language":      r.get("language", "en"),
            "symptoms_json": json.dumps(r.get("symptoms", []), ensure_ascii=False),
            "red_flags":     r.get("red_flags", []),
        })

df = pd.DataFrame(rows)
print(f"  corpus: {len(df)} rows  EN={sum(df.language=='en')}  HI={sum(df.language=='hi')}")

# Verify 3 demo specialties present
for sp in ("Cardiology", "Orthopedics", "Nephrology"):
    n = sum(df.specialty == sp)
    assert n > 0, f"required specialty missing: {sp}"
    print(f"  {sp}: {n} entries ✓")

# mkstemp is the safe non-deprecated variant (mktemp has a TOCTOU race) and
# atexit cleanup ensures the parquet is removed on normal exit / Ctrl-C, so
# repeated runs don't leak files into /tmp.
_fd, local_parquet = tempfile.mkstemp(suffix=".parquet")
os.close(_fd)
atexit.register(lambda p=local_parquet: os.path.exists(p) and os.unlink(p))
df.to_parquet(local_parquet, index=False)
print(f"  parquet: {os.path.getsize(local_parquet)} bytes → {local_parquet}")


# ── 2. ensure UC Volume exists, upload ────────────────────────────────────────

print("\n→ ensuring UC Volume workspace.default.raw...")
subprocess.run(
    ["databricks", "volumes", "create",
     "workspace", "default", "raw", "MANAGED", "-p", PROFILE],
    capture_output=True,
)

print(f"→ uploading to {VOLUME_PATH}...")
sh(["databricks", "fs", "cp", local_parquet, f"dbfs:{VOLUME_PATH}",
    "-p", PROFILE, "--overwrite"])
print("  upload ✓")


# ── 3. CREATE OR REPLACE TABLE with PK + CDF ─────────────────────────────────

print(f"\n→ creating {TABLE} (PK=id, CDF=true)...")
sql(f"""
CREATE OR REPLACE TABLE {TABLE} (
  id            STRING NOT NULL,
  text          STRING,
  specialty     STRING,
  urgency       INT,
  language      STRING,
  symptoms_json STRING,
  red_flags     ARRAY<STRING>,
  CONSTRAINT symptom_corpus_pk PRIMARY KEY (id)
) TBLPROPERTIES (delta.enableChangeDataFeed = true)
""")
print("  CREATE ✓")


# ── 4. INSERT from parquet ────────────────────────────────────────────────────

print(f"→ inserting rows from parquet volume...")
sql(f"""
INSERT INTO {TABLE}
SELECT id, text, specialty, urgency, language, symptoms_json, red_flags
FROM parquet.`{VOLUME_PATH}`
""")
print("  INSERT ✓")


# ── 5. smoke count ────────────────────────────────────────────────────────────

print(f"\n→ smoke: SELECT count(*) FROM {TABLE}")
d = sql(f"SELECT count(*) AS n FROM {TABLE}")
n = int(d["result"]["data_array"][0][0])
print(f"  count = {n}")
assert n >= 10, f"expected >= 10 rows, got {n}"
print(f"\n✓ {TABLE} ready  ({n} rows, PK=id, CDF=true)")
