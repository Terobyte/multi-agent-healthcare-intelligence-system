#!/usr/bin/env python3
"""Create Mubarak's Vector Search endpoint + Delta-sync index over symptom_corpus.

Steps:
  1. (Pre-req) symptom_corpus table must already exist with CDF=true — run
     01_symptom_corpus.py first.
  2. Create VS endpoint `mubarak_vs` (idempotent — skipped if already exists).
  3. Poll endpoint state until ONLINE (max 15 min).
  4. Create Delta-sync index (TRIGGERED) over workspace.default.symptom_corpus
     using databricks-bge-large-en embeddings on the `text` column.
  5. Smoke: verify index state is ONLINE or ONLINE_NO_PENDING_UPDATE.

Usage:
  cd healthcare
  python3 mubarak/triage/02_vs_endpoint.py

Env vars:
  DBX_PROFILE  (default tero2)
  DBX_WH       (default 10fff96dd6d936b5)
  VS_ENDPOINT  (default mubarak_vs)    ← also in .env / .env.example

Notes:
  - Databricks Trial allows 1 VS endpoint. If vs_healthcare is already ONLINE,
    you may need to delete it first or use the same endpoint for both indexes.
  - TRIGGERED pipeline type: index syncs on demand, not continuously.
    Call POST .../sync to trigger a manual sync after table updates.
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

PROFILE    = os.environ.get("DBX_PROFILE", "tero2")
WH         = os.environ.get("DBX_WH", "10fff96dd6d936b5")
ENDPOINT   = os.environ.get("VS_ENDPOINT", "vs_healthcare")  # Trial: 1 endpoint max; reuse vs_healthcare
SOURCE_TABLE = "workspace.default.symptom_corpus"
INDEX_NAME   = "workspace.default.symptom_corpus_idx"
EMBED_MODEL  = "databricks-bge-large-en"
PRIMARY_KEY  = "id"
EMBED_COL    = "text"


# ── helpers ───────────────────────────────────────────────────────────────────

def sh(cmd, check=True):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if check and r.returncode != 0:
        print((r.stderr or r.stdout)[:500], file=sys.stderr)
        sys.exit(r.returncode)
    return r.stdout


def api(method, path, body=None):
    """Call Databricks REST API; tolerate non-zero exit when stdout is valid JSON."""
    cmd = ["databricks", "api", method, "-p", PROFILE, path]
    if body is not None:
        cmd += ["--json", json.dumps(body)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    out = r.stdout or ""
    if r.returncode != 0 and not out.strip():
        print(
            f"  api({method} {path}) failed rc={r.returncode}: "
            f"{(r.stderr or '').strip()[:200]}",
            file=sys.stderr,
        )
        return {}
    if not out.strip():
        return {}
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        print(f"  api({method} {path}) non-JSON: {out[:200]}", file=sys.stderr)
        return {}


# ── Step 1 guard — confirm source table exists AND has CDF enabled ───────────
# Delta-sync Vector Search indexes REQUIRE Change Data Feed on the source table.
# DESCRIBE DETAIL only proves existence; we need SHOW TBLPROPERTIES to verify
# delta.enableChangeDataFeed=true, otherwise index creation will fail later.

def _run_sql(statement: str) -> dict:
    payload = json.dumps({
        "statement": statement,
        "warehouse_id": WH,
        "wait_timeout": "30s",
    })
    out = sh(["databricks", "api", "post", "-p", PROFILE,
              "/api/2.0/sql/statements", "--json", payload])
    return json.loads(out)


print(f"→ confirming source table {SOURCE_TABLE} exists...")
d = _run_sql(f"DESCRIBE DETAIL {SOURCE_TABLE}")
if d.get("status", {}).get("state") == "FAILED":
    msg = d["status"].get("error", {}).get("message", "unknown")
    print(f"✗ source table not found: {msg}", file=sys.stderr)
    print("  Run 01_symptom_corpus.py first.", file=sys.stderr)
    sys.exit(2)
print(f"  ✓ {SOURCE_TABLE} exists")

print(f"→ verifying Change Data Feed is enabled on {SOURCE_TABLE}...")
d = _run_sql(f"SHOW TBLPROPERTIES {SOURCE_TABLE}")
if d.get("status", {}).get("state") == "FAILED":
    msg = d["status"].get("error", {}).get("message", "unknown")
    print(f"✗ SHOW TBLPROPERTIES failed: {msg}", file=sys.stderr)
    sys.exit(2)
rows = d.get("result", {}).get("data_array", []) or []
props = {row[0]: row[1] for row in rows if len(row) >= 2}
cdf = props.get("delta.enableChangeDataFeed", "false").lower()
if cdf != "true":
    print(
        f"✗ {SOURCE_TABLE} does not have CDF enabled "
        f"(delta.enableChangeDataFeed={cdf!r}).",
        file=sys.stderr,
    )
    print("  Delta-sync Vector Search indexes REQUIRE CDF. Fix with:",
          file=sys.stderr)
    print(
        f"    ALTER TABLE {SOURCE_TABLE} SET TBLPROPERTIES "
        "(delta.enableChangeDataFeed = true);",
        file=sys.stderr,
    )
    sys.exit(3)
print(f"  ✓ delta.enableChangeDataFeed=true")


# ── Step 2 — create endpoint (idempotent) ────────────────────────────────────

print(f"\n→ checking VS endpoint {ENDPOINT!r}...")
existing = api("get", "/api/2.0/vector-search/endpoints").get("endpoints", [])
if any(e.get("name") == ENDPOINT for e in existing):
    print(f"  endpoint {ENDPOINT!r} already exists — skipping create")
else:
    print(f"  creating endpoint {ENDPOINT!r}...")
    r = api(
        "post",
        "/api/2.0/vector-search/endpoints",
        {"name": ENDPOINT, "endpoint_type": "STANDARD"},
    )
    print(f"  create response: {r.get('endpoint_status', r)}")


# ── Step 3 — poll endpoint until ONLINE (max 15 min) ─────────────────────────

print(f"\n→ polling endpoint state (up to 15 min)...")
for i in range(60):
    e = api("get", f"/api/2.0/vector-search/endpoints/{ENDPOINT}")
    state = e.get("endpoint_status", {}).get("state", "?")
    print(f"  [{i * 15}s] state={state}")
    if state == "ONLINE":
        print(f"  ✓ endpoint ONLINE")
        break
    if state in ("OFFLINE", "FAILED"):
        sys.exit(f"✗ endpoint went {state}: {e}")
    time.sleep(15)
else:
    sys.exit("✗ endpoint did not become ONLINE within 15 min")


# ── Step 4 — create Delta-sync index (TRIGGERED, idempotent) ─────────────────

print(f"\n→ checking index {INDEX_NAME!r}...")
existing_idx = api(
    "get",
    f"/api/2.0/vector-search/endpoints/{ENDPOINT}/indexes",
).get("vector_indexes", [])

if any(idx.get("name") == INDEX_NAME for idx in existing_idx):
    print(f"  index {INDEX_NAME!r} already exists — skipping create")
else:
    print(f"  creating Delta-sync index (TRIGGERED) {INDEX_NAME!r}...")
    r = api(
        "post",
        "/api/2.0/vector-search/indexes",
        {
            "name": INDEX_NAME,
            "endpoint_name": ENDPOINT,
            "primary_key": PRIMARY_KEY,
            "index_type": "DELTA_SYNC",
            "delta_sync_index_spec": {
                "source_table": SOURCE_TABLE,
                "pipeline_type": "TRIGGERED",
                "embedding_source_columns": [
                    {
                        "name": EMBED_COL,
                        "embedding_model_endpoint_name": EMBED_MODEL,
                    }
                ],
            },
        },
    )
    print(f"  create response: {r.get('status', r)}")


# ── Step 5 — smoke: confirm index is reachable ────────────────────────────────

print(f"\n→ checking index status...")
idx = api("get", f"/api/2.0/vector-search/indexes/{INDEX_NAME}")
detail_state = idx.get("status", {}).get("detailed_state", "?")
indexed_rows = idx.get("status", {}).get("indexed_row_count", 0)
print(f"  state={detail_state}  indexed_row_count={indexed_rows}")

if detail_state not in ("ONLINE", "ONLINE_NO_PENDING_UPDATE", "INITIAL_SYNC_IN_PROGRESS"):
    print(
        f"\n  Note: index state is {detail_state!r}. Initial sync may still be running.\n"
        "  Re-run this script after a few minutes to confirm ONLINE state.\n"
        "  To trigger a manual sync later:\n"
        f"    databricks api post -p {PROFILE} "
        f"/api/2.0/vector-search/indexes/{INDEX_NAME}/sync"
    )
else:
    print(f"  ✓ index reachable (state={detail_state})")

print(f"""
✓ Setup complete
  Endpoint : {ENDPOINT}
  Index    : {INDEX_NAME}
  Source   : {SOURCE_TABLE}  (PK={PRIMARY_KEY}, embed_col={EMBED_COL})
  Pipeline : TRIGGERED (sync on demand)

To trigger first sync:
  databricks api post -p {PROFILE} /api/2.0/vector-search/indexes/{INDEX_NAME}/sync
""")
