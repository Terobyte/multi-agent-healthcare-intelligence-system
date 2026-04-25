#!/usr/bin/env python3
"""Execute a SQL file with multiple `;`-terminated statements via Databricks SQL Statement API.
The single-statement dbq.py only handles ONE statement — use this for DDL files with multiple CREATEs.

Usage: python3 run_sql_file.py <path/to/file.sql>
"""
import json, os, subprocess, sys

WH = os.environ.get("DBX_WH", "10fff96dd6d936b5")
PROFILE = os.environ.get("DBX_PROFILE", "tero2")

if len(sys.argv) < 2:
    sys.exit("usage: run_sql_file.py <file.sql>")

sql = open(sys.argv[1]).read()
stmts, buf = [], []
for line in sql.split("\n"):
    if line.lstrip().startswith("--") or not line.strip():
        continue
    buf.append(line)
    if line.rstrip().endswith(";"):
        stmts.append("\n".join(buf).rstrip(";").strip())
        buf = []

print(f"running {len(stmts)} statements from {sys.argv[1]}")
for i, stmt in enumerate(stmts, 1):
    payload = json.dumps({"statement": stmt, "warehouse_id": WH, "wait_timeout": "50s"})
    r = subprocess.run(["databricks","api","post","-p",PROFILE,"/api/2.0/sql/statements","--json",payload],
                       capture_output=True, text=True)
    d = json.loads(r.stdout) if r.stdout else {}
    state = d.get("status",{}).get("state","?")
    err = d.get("status",{}).get("error",{}).get("message","")
    head = stmt.split("\n",1)[0][:80]
    print(f"  [{i}/{len(stmts)}] {state}  {head}")
    if err:
        print(f"      ERR: {err[:300]}")
        sys.exit(2)
