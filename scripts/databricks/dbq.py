#!/usr/bin/env python3
"""Quick Databricks SQL via CLI. Usage: python3 dbq.py "SELECT ..."
Override profile/warehouse with env vars: DBX_PROFILE, DBX_WH."""
import json, os, subprocess, sys

WH = os.environ.get("DBX_WH", "10fff96dd6d936b5")
PROFILE = os.environ.get("DBX_PROFILE", "tero2")
sql = sys.argv[1] if len(sys.argv) > 1 else sys.stdin.read()

payload = json.dumps({"statement": sql, "warehouse_id": WH, "wait_timeout": "50s"})
r = subprocess.run(
    ["databricks", "api", "post", "-p", PROFILE, "/api/2.0/sql/statements", "--json", payload],
    capture_output=True, text=True, timeout=60
)
try:
    d = json.loads(r.stdout)
except Exception:
    print("RAW STDOUT:", r.stdout[:500])
    print("STDERR:", r.stderr[:500])
    sys.exit(1)

status = d.get("status", {}).get("state", "?")
if status == "FAILED":
    err = d.get("status", {}).get("error", {}).get("message", "?")
    print(f"FAILED: {err}")
    sys.exit(2)

if "result" in d and "data_array" in d.get("result", {}):
    cols = [c["name"] for c in d["manifest"]["schema"]["columns"]]
    rows = d["result"]["data_array"]
    widths = [max(len(str(c)), max((len(str(r[i])) for r in rows), default=0)) for i, c in enumerate(cols)]
    print("  ".join(c.ljust(widths[i]) for i, c in enumerate(cols)))
    print("  ".join("-" * widths[i] for i in range(len(cols))))
    for r in rows:
        print("  ".join(str(v if v is not None else "NULL").ljust(widths[i]) for i, v in enumerate(r)))
    print(f"\n[{len(rows)} rows]")
else:
    print(json.dumps(d, indent=2)[:600])
