# Multi-Agent Healthcare Intelligence System

HackNation 2026 submission for **Challenge 3 — Agentic Healthcare Maps** (Databricks).

> We don't show hospitals — we guide patients to the right care at the right time.
> Maps + multi-agent triage + atomic booking + outcome learning loop.

## What it does

A patient enters symptoms (text or Hindi/Urdu voice). The system:

1. **Triage agent** classifies the case to a specialty (vector-search over a symptom corpus, with LLM fallback).
2. **Router agent** ranks nearby hospitals by `P(bed available) × travel time × specialty match × calibrated trust`.
3. **Atomic booking saga** reserves bed + ambulance + doctor + drug in a single transaction — if any leg fails, all four are rolled back.
4. **Outcome ledger** records patient pings after care, which **recalibrates trust scores** for future patients.
5. **Reasoning stream** broadcasts every agent decision over SSE so the UI shows the "why" live.

A second app (NGO Dashboard) maps **3,736 Indian PINs** by capability gaps — e.g. *Bihar: 149 PINs with zero oncology, 130 with zero emergency*. A third (Doctor Copilot) is the clinician-side referral view.

## Architecture

| Layer | Stack |
|---|---|
| Frontend | React 18 + Vite + TypeScript + Tailwind + Leaflet (`arushi/app/`) |
| Backend | FastAPI + slowapi rate-limiting + SSE (`app/`) |
| Data | Databricks SQL Warehouse, Vector Search (BGE-large), Foundation Model APIs (Llama 3.3 70B + Llama 4 Maverick consensus, GPT-5.x as fallback) |
| Hosting | Railway (backend, autodeploys on `main`) + Vercel (frontend) |

10,000 facilities ingested → cleaned → trust-scored via two-model LLM consensus → 4-tier badge (`rule / single-LLM / two-model-verified / models-disagree`) materialised in `gold_trust_final`.

## Killing features

- **Trust calibration via two-model LLM consensus.** Llama 3.3 70B (Extractor) + Llama 4 Maverick (Validator) score each facility on 4 sub-factors; agreement-band logic decides whether the trust score is `verified`, `single-source`, or `disagreement`. ~$0.30 total LLM cost for 256 facilities.
- **Atomic booking saga.** `txn_atomic` + 4 resource tables (bed, ambulance, doctor, drug). Compensating-action rollback on any leg failure. Demo includes a deliberate `ambulance unavailable` saga that rolls back all four resources.
- **Outcome learning loop.** Patient pings after care write to `outcome_feedback` → `v_trust_calibrated` view recomputes trust on the fly. Demo arc: *Aradhna 0.831 → 0.350* after 6 negative outcomes.
- **Vernacular voice triage.** Web Speech API for Hindi/Urdu input on patient side; Fish Audio TTS narrates ambulance dispatch in Hindi/Urdu after `/book` commits.
- **NGO Desert Map.** Per-PIN capability heatmap exposes coverage gaps (density ≠ access — *Maharashtra has 1,492 facilities but 403 PINs with zero oncology*).
- **Reasoning stream (SSE).** `/sse` emits structured events as agents decide — frontend renders the chain in real time, no polling.
- **Token-scrubbing logger.** Global `LogRecordFactory` redacts `dapi*`, `sk-*`, and Fish-key shapes from every log line and traceback before they hit any handler.

## Live URLs

- **API:** https://aarogyanet-api-production.up.railway.app — try `/health`, `/docs` (Swagger), `/triage`
- **Web:** https://app-wine-pi.vercel.app

## Run locally

### Backend (Python 3.11+)

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env       # fill DATABRICKS_HOST/TOKEN/WAREHOUSE_ID, DEMO_KEY, PII_SALT
uvicorn app.main:app --reload --port 8000
```

Hit `http://localhost:8000/docs` for the Swagger UI.

If you don't have Databricks credentials, the triage agent falls back to a keyword corpus and the router serves canned data — most routes still respond, just without live trust calibration.

### Frontend (Node 18+)

```bash
cd arushi/app
npm install
npm run dev                # http://localhost:5173
```

The frontend resolves to live API by default. To point at a local backend:

```bash
echo "VITE_PUBLIC_URL=http://localhost:8000" > .env.local
echo "VITE_DEMO_KEY=<same value as backend .env DEMO_KEY>" >> .env.local
```

If `VITE_PUBLIC_URL` is unset and the live API is unreachable, the app uses the mocks under `arushi/app/mocks/` — useful for pure-frontend work.

### Smoke test

```bash
bash scripts/smoke_railway.sh   # checks /health, /triage, /sse, /book on the live API
```

## Branch: `feat/sponsor-stack`

This branch adds **opt-in sponsor-criteria features** that wrap the existing endpoints. All flag-gated, all default off, all importable as no-ops:

| Flag | Mounts | What it does |
|---|---|---|
| `SPONSOR_AGENT_BRICKS=true` | `POST /sponsor/triage` | MLflow `ResponsesAgent` wrapper around `triage()` — pitches Mosaic AI Agent Framework conformance |
| `SPONSOR_GENIE=true` | `POST /sponsor/genie/query` | Databricks Genie client (canned by default; live with `SPONSOR_GENIE_LIVE=true`) |
| `SPONSOR_VOICE=true` | `POST /sponsor/narrate` | Fish Audio TTS narration in Hindi/Urdu after booking |
| `SPONSOR_KA=true` | (internal) | Knowledge Assistant stub — JSON-corpus fallback; real wiring deferred |
| `SAFE_DEMO=true` | — | Master kill-switch: every sponsor route returns a pre-baked artifact from `app/sponsor/_demo/`. Stage-day insurance. |

Every public sponsor route is gated by `Depends(require_demo_key)` + slowapi limits. Token-scrub patterns are extended to cover `sk-*` and Fish keys when the package is imported.

See `SPONSOR_STACK_PLAN.md` for the full v2 scope, drop list, and pre-demo rehearsal checklist.

## Project layout

```
app/                   # FastAPI backend
├── agents/            # triage, router, booking, validator, reasoning_stream
├── sponsor/           # opt-in sponsor stack (branch: feat/sponsor-stack)
├── main.py            # FastAPI app + endpoints
├── db.py              # Databricks SQL warehouse client
├── schemas.py         # Pydantic models (TriageOutput, BookingOutput, …)
└── settings.py        # env-backed config

arushi/app/            # React + Vite frontend
├── src/
│   ├── pages/         # PatientFlow, DoctorCopilot, NGODashboard
│   ├── components/    # HospitalMap, ChatInput, ReasoningPanel, AtomicBookingTiles, …
│   └── lib/           # api.ts, types.ts
└── mocks/             # local fallback when backend unreachable

contracts/             # shared Pydantic schemas (RankedHospital, …)
docs/                  # challenge brief, runbook, progress notes
scripts/               # databricks/ (data layer), sponsor/, smoke_railway.sh
tests/                 # pytest — agents, calibration, contracts, scrub
data/llm_artifacts/    # committed LLM scoring outputs (small, reproducible)
```

## Endpoints (core)

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Liveness + warehouse reachability |
| POST | `/triage` | Symptoms → specialty + urgency |
| POST | `/recommend` | Triage output + location → ranked hospitals |
| POST | `/book` | Atomic 4-resource booking saga (auth: `X-Demo-Key`) |
| POST | `/outcome` | Patient ping → outcome ledger (auth) |
| GET | `/ngo-data` | NGO dashboard PINs + capability gaps |
| GET | `/sse` | Reasoning stream (Server-Sent Events) |
| GET | `/sse_demo` | Pre-recorded reasoning stream for offline demo |
| GET | `/docs` | Swagger UI |

## Tests

```bash
pytest                                    # all
pytest tests/test_router_calibration.py   # router trust-weighting
pytest app/sponsor/tests/                 # sponsor modules
```

Live integration tests are gated behind `@pytest.mark.live` + env-var presence; CI runs unit tests only.

## Deploy

- **Backend:** push to `main` → Railway autodeploys via `Procfile` (`uvicorn app.main:app --host 0.0.0.0 --port $PORT`).
- **Frontend:** `cd arushi/app && vercel --prod` (no auto-deploy from Git by default — set up in Vercel dashboard if desired).

`DEMO_KEY` must match across local `.env`, Railway Variables, and Vercel Environment Variables — `/book` and `/outcome` validate it via the `X-Demo-Key` header.

## License

Hackathon submission — see repository for terms.
