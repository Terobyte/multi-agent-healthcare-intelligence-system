#!/usr/bin/env bash
# Smoke-check the deployed frontend against the Railway backend.
#
# Usage:
#   bash scripts/smoke_frontend_backend.sh
#   bash scripts/smoke_frontend_backend.sh https://app-wine-pi.vercel.app https://aarogyanet-api-production.up.railway.app

set -u

APP_URL="${1:-https://app-wine-pi.vercel.app}"
API_URL="${2:-https://aarogyanet-api-production.up.railway.app}"

G="\033[0;32m"; R="\033[0;31m"; Y="\033[0;33m"; N="\033[0m"
pass() { printf "${G}OK${N}  %s\n" "$1"; }
fail() { printf "${R}FAIL${N} %s\n" "$1"; }
warn() { printf "${Y}WARN${N} %s\n" "$1"; }

tmpdir="${TMPDIR:-/tmp}/aarogyanet-smoke"
mkdir -p "$tmpdir"

echo "Smoking frontend $APP_URL"
echo "Against backend $API_URL"
echo "---"

curl -fsS --max-time 20 "$APP_URL" -o "$tmpdir/index.html" \
  || { fail "frontend index fetch failed"; exit 1; }
asset="$(grep -oE '/assets/index-[A-Za-z0-9_-]+\.js' "$tmpdir/index.html" | head -1)"
if [ -z "$asset" ]; then fail "frontend index asset not found"; exit 1; fi
pass "frontend index references $asset"

curl -fsS --max-time 20 "$APP_URL$asset" -o "$tmpdir/bundle.js" \
  || { fail "frontend bundle fetch failed"; exit 1; }
if grep -q "$API_URL" "$tmpdir/bundle.js"; then
  pass "frontend bundle contains backend URL"
else
  fail "frontend bundle does not contain expected backend URL"
  exit 1
fi

health="$(curl -fsS --max-time 20 "$API_URL/health" 2>&1)" \
  || { fail "backend /health failed"; echo "$health"; exit 1; }
echo "health: $health"
echo "$health" | grep -q '"status":"ok"' && pass "backend health ok" || warn "backend health not status=ok"

recommend_file="$tmpdir/recommend.json"
curl -fsS --max-time 40 -X POST "$API_URL/recommend" \
  -H "Origin: $APP_URL" \
  -H "Content-Type: application/json" \
  --data '{"user_text":"Auto triage critical care options nearby.","language_hint":"en"}' \
  -o "$recommend_file" \
  || { fail "backend /recommend failed"; exit 1; }

node --input-type=module - "$recommend_file" <<'NODE'
import fs from "node:fs";
const file = process.argv[2];
const data = JSON.parse(fs.readFileSync(file, "utf8"));
if (!Array.isArray(data.hospitals) || data.hospitals.length === 0) {
  console.error("recommend response has no hospitals");
  process.exit(1);
}
const first = data.hospitals[0];
const id = first.facility_id ?? first.hospital_id;
if (!id || !first.name || !Number.isFinite(first.lat) || !Number.isFinite(first.lon)) {
  console.error("first hospital is missing supported id/name/lat/lon fields");
  console.error(JSON.stringify(first, null, 2));
  process.exit(1);
}
console.log(`OK  /recommend returned ${data.hospitals.length} hospitals; first=${id} ${first.name}`);
NODE
rc=$?
if [ "$rc" -ne 0 ]; then fail "recommend response shape unsupported"; exit "$rc"; fi

ngo_status="$(curl -sS --max-time 20 -o /dev/null -w '%{http_code}' "$API_URL/ngo-data")"
if [ "$ngo_status" = "200" ]; then
  pass "/ngo-data returns 200"
else
  warn "/ngo-data returns $ngo_status; frontend should fall back locally without poisoning Patient degraded state"
fi

echo "---"
pass "Smoke complete."
