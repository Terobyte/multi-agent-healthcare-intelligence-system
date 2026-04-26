# AarogyaNet — Pitch Brief

**HackNation 2026, Challenge 3 — Databricks Agentic Healthcare Maps.**
Briefing for the tech lead and the product/PM person on the team.
Last updated: 2026-04-26.

---

## 0. What's deployed and verified live (right now)

| Component | URL | Status |
|---|---|---|
| Backend FastAPI | `https://aarogyanet-api-production.up.railway.app` | ✅ `/health` returns ok, `fm_ok=true`, 20 FM endpoints, warehouse configured |
| `/triage` | `POST` `{user_text, language_hint}` | ✅ Real LLM: chest pain → `{specialty:cardiology, urgency:4, fast_path:true, red_flag_match:[chest pain]}` |
| `/ngo-data` | `GET` | ✅ Returns 3,736 PINs with `severity:high` across 4 specialties (Trauma / Cardiac / Neuro / Pediatric) |
| `/sse_demo?session_id=X` | SSE stream | ✅ Streams `triage → extractor → validator → router` events with trace_id |
| Frontend | `https://app-wine-pi.vercel.app` | ✅ 200 OK |
| Databricks workspace | `dbc-17e9d40d-5056` | ✅ profile `tero2`, warehouse `10fff96dd6d936b5` |

**Credentials in place** (local `.env` + reference memory):
- `DATABRICKS_HOST/TOKEN/WAREHOUSE_ID` — real, token `dapi50bd6...`
- `DEMO_KEY=a1570b...` — used by `/book` and `/outcome` via `X-Demo-Key` header
- `PII_SALT` — used to hash patient_id before warehouse insert
- Dashboards: `vercel.com/terobytes-projects/app`, `railway.app → aarogyaNet-api`

---

## 1. Architecture in one picture

```
Patient (Hindi/Urdu voice or text)
        │
        ▼
   /triage  ──── Vector Search BGE-large + Llama 3.3 fallback
        │       (specialty, urgency, fast_path, red_flag_match)
        ▼
   /recommend  ── Router agent: P(bed) × travel × specialty × calibrated trust
        │       Trust = two-model consensus (Llama 3.3 + Llama 4 Maverick)
        │       4-tier badge: rule / single-LLM / verified / disagreement
        │       SSE: triage → extractor → validator → router events
        ▼
   /book   ──── Atomic saga: bed + ambulance + doctor + drug
        │       txn_atomic; failure on ANY leg → rollback all 4
        │       hash_patient_id before warehouse insert (bug #3 fix)
        ▼
   /outcome ─── Patient ping after care
        │       v_trust_calibrated view recomputes trust on the fly
        ▼
   Demo arc: Aradhna trust 0.831 → 0.350 after 6 negative outcomes
```

In parallel — three UI surfaces:
- **PatientFlow** — Leaflet map, 3 ranked hospitals, ChatInput, AtomicBookingTiles, ReasoningPanelSSE
- **DoctorCopilot** — referral copilot for clinicians
- **NGODashboard** — heatmap over 3,736 PINs by capability gaps ("Bihar: 149 PINs with zero oncology")

---

## 2. The killer feature — what to tell the judges

Of the 7 features listed in the README, here is the priority order for pitch:

### 🥇 The Killer = two-model trust consensus + atomic saga + outcome loop = a closed feedback cycle

This is **one story, not three**. Why it lands:

1. **Two-model consensus.** Llama 3.3 70B Extractor + Llama 4 Maverick Validator score each facility on 4 sub-factors → agreement-band logic → 4-tier badge (`verified / single-source / disagreement / rule`). 262 facilities went through the LLM path: **139 two-model verified**, **110 surfaced as `models-disagree`** (human-review), 13 single-LLM verified. The remaining 9,738 stay on rule-based heuristics until cost allows wider rollout. Total LLM cost ~$0.30. This is an **anti-hallucination guardrail** — most hackathon teams trust a single LLM. We don't.
2. **Atomic 4-resource saga** with compensating rollback. The demo includes a **deliberate failure**: "ambulance unavailable" → all four tiles roll back live. This is the kind of **distributed-transactions discipline** the Databricks judges recognise instantly. Hackathon chatbots cannot do this.
3. **Outcome learning loop with real arithmetic** — `Aradhna 0.831 → 0.350` after 6 negative outcomes. This closes the loop: the AI doesn't just recommend — it **learns**. Most demos cut off here. Ours doesn't.

### 🥈 NGO Desert Map — civil-society hook for the non-technical judges

"Maharashtra: 1,506 facilities, **403 of 443 PINs with zero oncology** (91.0%)." Density ≠ access. This is the emotional hook that works on any panel. And it's a **second product on the same data layer** — shows platform maturity.

### 🥉 Vernacular voice (Hindi/Urdu) — sponsor-criteria credit

Web Speech API on the patient side + Fish Audio TTS narration after `/book`. Not a killer on its own, but it adds an **inclusivity narrative** and another sponsor-friendly box ticked.

---

## 3. Pitch path — 60-second arc

| Sec | Scene | What to say |
|---|---|---|
| 0–10 | **Hook** | "When someone has a heart attack in Mumbai, Google Maps shows the nearest hospital. But **nearest ≠ best**. It might be full, it might lack a cardiologist, it might be unsafe. We guide patients to the right care at the right time." |
| 10–25 | **Patient demo** | Hindi voice input → triage classifies cardiology u4 fast_path → map with 3 hospitals, **trust badges visible** (verified / disagreement) + cost + ETA |
| 25–40 | **Atomic saga drama** | Click reserve → 4 tiles light up: bed ✓, doctor ✓, drug ✓, ambulance ✗ → **all four roll back**. "If even one resource fails — we don't promise the patient anything we can't deliver." |
| 40–50 | **Outcome loop** | Swipe to Doctor Copilot → "this clinic was trust 0.831, after 6 negative patient outcomes — 0.350. Trust learns in real time." |
| 50–58 | **NGO map** | "And the other side: 403 PINs in Maharashtra with no oncology at all. Density ≠ access." |
| 58–60 | **Close** | "**AarogyaNet — guide care, don't just map it.**" |

---

## 4. Brief for the tech lead

**Stack:**
- Backend: FastAPI + slowapi + SSE, Python 3.11, Pydantic, MLflow `ResponsesAgent`
- Data: Databricks SQL Warehouse + Vector Search (BGE-large) + Foundation Model APIs (Llama 3.3 70B + Llama 4 Maverick + GPT-5.x fallback)
- Frontend: React 18 + Vite + TS + Tailwind + Leaflet + framer-motion
- Hosting: Railway autodeploy on `git push origin main` (Procfile-driven uvicorn) + Vercel manual `vercel --prod` from `arushi/app/`
- Auth: `X-Demo-Key` header on `/book` and `/outcome`; `DEMO_KEY` is synced across local `.env`, Railway, and Vercel

**What's done** (per `bugs.md` and live probes):
- ✅ A1 booking saga (atomic 4-resource, rollback)
- ✅ A2 `/triage` (live LLM)
- ✅ A3 `/recommend` (router with trust calibration)
- ✅ SSE reasoning stream
- ✅ NGO data endpoint (3,736 PINs)
- ✅ `/sse_demo` for offline pre-recorded fallback
- ✅ Token-scrubbing logger (bug #20 — global LogRecordFactory)
- ✅ `hash_patient_id` wired into booking flow (bug #3)
- ✅ Sponsor stack on `feat/sponsor-stack`: Agent Bricks, Genie, Fish TTS, KA stub — all flag-gated, default off, `SAFE_DEMO=true` is the master kill-switch

**Known demo-day risks** (from the 20-agent sweep, `bugs.md:71-136`):
- bug #22: `/book` blocks the event loop (sync in async route) — **CRITICAL** if anyone hits it concurrently during the demo
- bug #23: SSE client-disconnect race — connection stays open after the client is gone
- bug #24: `StopIteration` crash in `_cost_estimate` when `trust_score < 0`
- bug #26: API parameter mismatch `lib/api.ts` vs backend — can 422 against the live API
- bug #33: EventSource memory leak in React StrictMode

**Failing-test-first discipline** is already in place: `tests/test_known_bugs_*.py`. Every MINE bug = failing test, flips RED → GREEN when fixed.

---

## 5. Brief for the PM / product person

**Three users, three apps, one data layer:**
1. **Patient app** — one-shot user journey: voice → triage → 3 ranked hospitals → reserve → confirmation. Hindi/Urdu inclusive.
2. **Doctor Copilot** — clinician-side referral flow with RAG-over-records, trust badges, ETA.
3. **NGO Dashboard** — analytics for health policy: "where the care deserts are."

**Differentiation for the judges** (in priority order):
- Not "an AI that gives advice" — **an AI that executes an atomic transaction** on real resources and **learns from outcomes**.
- Two-model trust consensus = anti-hallucination story (matters for healthcare regulation).
- NGO map = social-impact story (matters for non-technical judges).
- Sponsor stack — Databricks Agent Bricks, Genie, Vector Search, Foundation Models — all native, not bolted on.

**Demo robustness:**
- `SAFE_DEMO=true` flag = all sponsor routes return pre-baked artifacts from `app/sponsor/_demo/` — stage-day insurance if internet or Databricks die.
- `/sse_demo` = offline pre-recorded reasoning stream — if live `/sse` falls over, the narrative continues to work.
- Smoke script `scripts/smoke_railway.sh` validates `/health /triage /sse /book` after every deploy.

**Submission package = hidden critical track** (Arushi):
- README ✅ complete
- Demo video — in progress
- Devpost writeup — in progress
- GitHub polish — bugs.md cataloged, tests in place, README structured

**What I'd do before the demo** (if there's time):
1. Fix bug #22 (`/book` event loop block) — wrap with `asyncio.to_thread(book_atomic, ...)` — 5 minutes of work, saves us from a humiliating hang during live demo.
2. Fix bug #26 (api param mismatch) — otherwise the frontend will 422 against the live API.
3. Run `scripts/smoke_railway.sh` 30 minutes before the demo.
4. Flip `SAFE_DEMO=true` in Vercel env vars as a backup.

---

## 6. Tagline + one-liners (for slides, Devpost, ChannelMessage)

- **Tagline:** "Guide care, don't just map it."
- **One-liner for sponsor (Databricks):** "We use Databricks Vector Search + Foundation Model APIs + SQL Warehouse + MLflow Agent Bricks natively across triage, ranking, and outcome calibration — not as add-ons."
- **One-liner for non-technical jury:** "Google Maps shows you the nearest hospital. We show you the right one — and we book the bed, ambulance, doctor, and drug atomically. If any one fails, none get charged."
- **One-liner for clinical jury:** "Trust isn't a single LLM call. It's a two-model consensus, with a 4-tier confidence badge, recalibrated from real patient outcomes."

---

## 7. File map (where to dig if you need to)

```
app/                          # FastAPI backend
├── agents/
│   ├── triage.py             # /triage logic (vector search + LLM)
│   ├── router.py             # ranking + trust calibration
│   ├── booking.py            # atomic saga (4 resources, rollback)
│   ├── validator.py          # two-model consensus
│   └── reasoning_stream.py   # SSE event emitter
├── sponsor/                  # opt-in sponsor stack (feat/sponsor-stack)
│   ├── agent_bricks.py       # MLflow ResponsesAgent wrapper
│   ├── genie.py              # Databricks Genie client
│   ├── voice_narration.py    # Fish Audio TTS
│   └── _demo/                # pre-baked artifacts for SAFE_DEMO mode
├── main.py                   # FastAPI app + endpoints
├── db.py                     # Databricks SQL warehouse client
├── schemas.py                # Pydantic models
└── util.py                   # hash_patient_id, salt cache

arushi/app/                   # React + Vite frontend
├── src/pages/                # PatientFlow, DoctorCopilot, NGODashboard
├── src/components/           # HospitalMap, ChatInput, ReasoningPanelSSE, AtomicBookingTiles
├── src/lib/                  # api.ts, types.ts, adapter.ts
└── mocks/                    # local fallback when backend unreachable

bugs.md                       # 21-finding triage + 20-agent sweep, MINE/SCOPE/DISMISSED/INVALID
team.md                       # ownership map, GitHub-API audited skills
SPONSOR_STACK_PLAN.md         # sponsor-criteria features, flag matrix, demo rehearsal
README.md                     # public-facing project README
```
