#!/usr/bin/env python3
"""Execute a SQL file with multiple `;`-terminated statements via Databricks SQL Statement API.
The single-statement dbq.py only handles ONE statement — use this for DDL files with multiple CREATEs.

Usage: python3 run_sql_file.py <path/to/file.sql>
"""
import json, os, subprocess, sys
import sqlparse

WH = os.environ.get("DBX_WH", "10fff96dd6d936b5")
PROFILE = os.environ.get("DBX_PROFILE", "tero2")


def split_sql(sql: str) -> list[str]:
    """Split a SQL blob into individual statements using sqlparse.

    Handles semicolons inside string literals and block comments correctly,
    unlike naive `.split(";")`.
    """
    out: list[str] = []
    for raw in sqlparse.split(sql):
        cleaned = raw.strip().rstrip(";").strip()
        if cleaned:
            out.append(cleaned)
    return out


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit("usage: run_sql_file.py <file.sql>")

    with open(sys.argv[1], encoding="utf-8") as f:
        sql = f.read()
    stmts = split_sql(sql)

    print(f"running {len(stmts)} statements from {sys.argv[1]}")
    for i, stmt in enumerate(stmts, 1):
        _run_one(i, len(stmts), stmt)


def _run_one(i: int, total: int, stmt: str) -> None:
    payload = json.dumps({"statement": stmt, "warehouse_id": WH, "wait_timeout": "50s"})
    r = subprocess.run(["databricks","api","post","-p",PROFILE,"/api/2.0/sql/statements","--json",payload],
                       capture_output=True, text=True, timeout=60)
    head = stmt.split("\n",1)[0][:80]
    if r.returncode != 0:
        print(f"  [{i}/{total}] CLI_ERR  {head}")
        print(f"      STDERR: {(r.stderr or '').strip()[:300]}")
        sys.exit(2)
    d = json.loads(r.stdout) if r.stdout else {}
    state = d.get("status",{}).get("state","?")
    err = d.get("status",{}).get("error",{}).get("message","")
    print(f"  [{i}/{total}] {state}  {head}")
    if err or state == "FAILED":
        print(f"      ERR: {err[:300]}")
        sys.exit(2)


if __name__ == "__main__":
    main()
