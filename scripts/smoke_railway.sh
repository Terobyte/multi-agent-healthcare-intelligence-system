#!/usr/bin/env bash
# Smoke-check Railway deploy of aarogyaNet-api.
#
# Usage:
#   bash scripts/smoke_railway.sh
#   bash scripts/smoke_railway.sh https://other-url.up.railway.app
#
# Reads DEMO_KEY from local .env if available (needed for /book).

set -u

URL="${1:-https://aarogyanet-api-production.up.railway.app}"

if [ -f .env ]; then
  set -a; . ./.env; set +a
fi

G="\033[0;32m"; R="\033[0;31m"; Y="\033[0;33m"; N="\033[0m"
pass() { printf "${G}OK${N}  %s\n" "$1"; }
fail() { printf "${R}FAIL${N} %s\n" "$1"; }
warn() { printf "${Y}WARN${N} %s\n" "$1"; }

echo "Smoking $URL"
echo "---"

# 1. /health
HEALTH=$(curl -fs --max-time 15 "$URL/health" 2>&1) || { fail "curl /health failed"; exit 1; }
echo "1. /health -> $HEALTH"
if   echo "$HEALTH" | grep -q '"status":"ok"';       then pass "health ok"
elif echo "$HEALTH" | grep -q '"warehouse":"missing"'; then fail "DATABRICKS_WAREHOUSE_ID missing in Railway Variables"; exit 1
elif echo "$HEALTH" | grep -q '"fm_endpoints":null';   then fail "DATABRICKS_HOST or DATABRICKS_TOKEN missing in Railway Variables"; exit 1
elif echo "$HEALTH" | grep -q '"status":"degraded"';   then warn "degraded but creds present, continuing"
else fail "unexpected health response"; exit 1; fi
echo

# 2. /triage
TRIAGE=$(curl -fsX POST --max-time 30 "$URL/triage" \
  -H 'content-type: application/json' \
  -d '{"user_text":"chest pain"}' 2>&1) || { fail "curl /triage failed"; exit 1; }
echo "2. /triage chest pain -> $TRIAGE"
if echo "$TRIAGE" | grep -q '"specialty"'; then pass "triage returned a specialty"
else fail "triage response missing specialty field"; exit 1; fi
echo

# 3. /sse smoke (5s sample)
echo "3. /sse stream (5s sample) ..."
SSE=$(curl -N --max-time 5 "$URL/sse?session_id=tero_smoke" 2>&1 | head -10)
echo "$SSE" | head -5
if echo "$SSE" | grep -qE '^(event|data):'; then pass "SSE emitting events"
else warn "SSE may not be wired yet (non-blocking)"; fi
echo

# 4. /book (only if DEMO_KEY present locally)
if [ -n "${DEMO_KEY:-}" ]; then
  BOOK=$(curl -fsX POST --max-time 30 "$URL/book" \
    -H 'content-type: application/json' \
    -H "X-Demo-Key: $DEMO_KEY" \
    -d '{"facility_id":5603,"patient_text":"smoke test","required_bed_type":"icu"}' 2>&1)
  RC=$?
  echo "4. /book -> $BOOK"
  if [ $RC -eq 0 ] && echo "$BOOK" | grep -qE '"transaction_id"|"ROLLED_BACK"'; then pass "atomic saga responded"
  else warn "/book failed — check DEMO_KEY matches Railway Variables"; fi
else
  warn "DEMO_KEY not in local .env — skipping /book smoke"
fi

echo "---"
pass "Smoke complete."
echo
echo "Hand off to team:"
echo "  PUBLIC_URL=$URL"
