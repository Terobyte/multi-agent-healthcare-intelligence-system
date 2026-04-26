# Mubarak Bug Report

Last updated: 2026-04-26

## Scope

This report is based on a direct codebase review of the current repository state plus a local test attempt.

It focuses on:
- what the project actually is today
- which features are truly implemented versus demo-scaffolded
- confirmed bugs and integration gaps worth documenting for the team

## Project Summary

This project is a multi-agent healthcare routing demo for India. Its core workflow is:

1. Patient enters symptoms
2. Triage agent classifies urgency/specialty
3. Router ranks hospitals
4. Booking saga attempts to reserve multiple resources
5. Outcome feedback is written back for trust recalibration

User-facing surfaces currently in the repo:

- Patient flow UI: symptom input, hospital recommendation cards, booking UX
- Doctor copilot UI: transfer/referral-oriented dashboard
- NGO dashboard: underserved PIN/specialty map

Core backend implementation exists for:

- `/health`
- `/triage`
- `/recommend`
- `/book`
- `/outcome`
- `/ngo-data`
- `/sse`
- `/sse_demo`

Key code locations:

- `app/main.py`
- `app/agents/triage.py`
- `app/agents/router.py`
- `app/agents/booking.py`
- `arushi/app/src/pages/PatientFlow.tsx`
- `arushi/app/src/pages/DoctorCopilot.tsx`
- `arushi/app/src/pages/NGODashboard.tsx`

## Critical Assessment

The project is real and non-trivial. It is not just a slide deck or prompt wrapper. The backend has meaningful engineering work in it:

- request limits
- auth on mutating routes
- SSE streaming
- Databricks integration
- privacy helpers
- booking rollback logic
- a fairly large test suite

The strongest part of the project is the system story:

- triage
- ranking
- atomic booking
- outcome learning loop

That is a much better hackathon narrative than a plain chatbot or hospital finder.

The main weakness is end-to-end integration drift. Several parts of the frontend are still mock-backed or only loosely aligned with backend contracts, so the demo story is stronger than the actual integration quality.

Best description of current state:

> Strong backend/data hackathon build, partially real frontend integration, some demo-only scaffolding still visible.

## Findings

### Critical

#### 1. Frontend request contract drift on `/triage` and `/recommend`

- Severity: Critical
- Files:
  - `arushi/app/src/api.ts:115`
  - `arushi/app/src/api.ts:117`
  - `app/main.py:403`
  - `app/main.py:419`

The frontend sends `language_hint`, but the backend request models expect `language`.

Evidence:

- Frontend:
  - `/triage` sends `{ user_text, language_hint }`
  - `/recommend` sends `{ user_text, language_hint }`
- Backend:
  - `TriageRequest` expects `language`
  - `RecommendRequest` expects `city` and `language`

Impact:

- language selection from the frontend is not wired correctly
- backend will silently use default `"en"`
- recommend requests also omit `city`, so routing falls back to backend default city `"mumbai"`

Why this matters:

This is not just cosmetic. It means recommendation quality can be wrong while the UI still looks successful.

#### 2. `/outcome` appears to persist raw `patient_id`

- Severity: Critical
- Files:
  - `app/main.py:521`
  - `app/util.py:3`

The privacy helper explicitly says raw patient identifiers should not be logged or persisted after the utility layer, but the `/outcome` handler writes `fb.patient_id` directly into the warehouse MERGE payload.

Impact:

- likely privacy/compliance bug
- inconsistent with the project’s own PII-handling contract
- contradicts the stated approach already used in booking flow

Why this matters:

This is one of the highest-risk bugs because the repo explicitly claims privacy-conscious behavior.

#### 3. Booking code can emit a status not allowed by the API schema

- Severity: Critical
- Files:
  - `app/agents/booking.py:190`
  - `app/schemas.py:55`

`booking.py` can return `ROLLBACK_FAILED`, but `BookingOutput.status` only allows:

- `COMMITTED`
- `ROLLED_BACK`
- `REJECTED`

Impact:

- runtime validation/serialization failure possible on a real rollback failure path
- the exact path meant to expose consistency drift may instead break the response contract

Why this matters:

This is a real reliability bug hiding in an error-handling branch.

### High

#### 4. Patient reasoning panel is still mock-driven instead of using the real SSE stream

- Severity: High
- Files:
  - `arushi/app/src/pages/PatientFlow.tsx:81`
  - `arushi/app/src/lib/api.ts:191`
  - `arushi/app/src/components/ReasoningPanelSSE.tsx:47`

The patient page calls `streamReasoning()` from `lib/api.ts`, which loads mock reasoning tokens from local JSON. A real SSE component exists, but the main patient flow is not using it.

Impact:

- reasoning UI can appear live even when it is not connected to backend reasoning events
- demo can overstate real-time agent integration

Why this matters:

This weakens the truthfulness of the “live reasoning stream” claim.

#### 5. Doctor Copilot is partially mock-backed and missing real transfer route integration

- Severity: High
- Files:
  - `arushi/app/src/pages/DoctorCopilot.tsx:20`
  - `arushi/app/src/lib/api.ts:206`
  - `app/main.py`

`DoctorCopilot` loads recommendation data plus mock copilot context from `doctor-copilot.json`. There is also no real `/transfer` route in `app/main.py`.

Impact:

- doctor flow is present visually but not fully supported by backend
- referral PDF/transfer workflow is still incomplete

Why this matters:

This should be described honestly as a partial feature, not a fully implemented one.

#### 6. Test suite does not collect cleanly in current local environment

- Severity: High
- Files:
  - `app/db.py:4`
  - `requirements.txt:1`

Local command run:

```bash
pytest -q
```

Observed result:

- test collection failed
- `ModuleNotFoundError: No module named 'databricks'`

Impact:

- current local verification path is fragile
- contributors can be blocked before reaching actual tests

Notes:

- this may be an environment/setup issue rather than an application-code bug
- it still belongs in the report because it affects team velocity and bug triage

### Medium

#### 7. Frontend/backend feature naming and contract layering are drifting

- Severity: Medium
- Files:
  - `contracts/schemas.py`
  - `app/schemas.py`
  - `arushi/app/src/lib/types.ts`
  - `arushi/app/src/lib/adapter.ts`

There are multiple overlapping schema layers:

- shared contracts
- backend Pydantic models
- frontend legacy UI types
- frontend canonical backend types

Impact:

- greater chance of silent drift
- adapters become the place where bugs hide
- a request can “work” while using defaults or degraded assumptions

Why this matters:

This is a structural source of future bugs, especially during rapid hackathon merges.

#### 8. Repo contains stale or contradictory documentation

- Severity: Medium
- Files:
  - `README.md`
  - `docs/RESUME-HERE.md`
  - `docs/PLAN-REMAINING.md`

Examples seen during review:

- some docs still mention Render while the current deployment note says Railway
- planning docs describe routes/features that have since changed or only partially landed

Impact:

- new team members can misunderstand what is actually live
- bug ownership can get confused

### Low

#### 9. Repo hygiene issue: stray inaccessible pytest cache temp directories

- Severity: Low
- Evidence:
  - `git status --short` emitted permission warnings for temp cache directories

Impact:

- minor noise during repo operations
- can confuse contributors, especially when debugging test runs

## Implemented vs Demo-Scaffolded

### Looks genuinely implemented

- triage backend flow
- router backend flow
- booking saga backend flow
- outcome endpoint
- NGO data endpoint
- SSE backend endpoint
- Databricks SQL/data scripts

### Partially implemented or scaffolded

- patient-side live reasoning display
- doctor transfer copilot
- some frontend/backend request contract wiring
- full end-to-end multilingual/location-aware request flow

## Overall Verdict

This is a strong hackathon project with a real backend spine and a compelling product story.

Its biggest current problem is not lack of ambition. It is integration truth:

- some features are genuinely built
- some features are visually present but still mock-backed
- some contracts have drifted enough to create silent wrong behavior

If this project is being audited for bugs, the highest-value areas to focus next are:

1. request/response contract mismatches
2. privacy handling around patient identifiers
3. booking error-path schema correctness
4. replacing mock reasoning flow with real SSE wiring
5. tightening test/setup reproducibility

## Local Verification Notes

Reviewed directly from repository code on 2026-04-26.

Attempted test run:

```bash
pytest -q
```

Result:

- failed during collection because `databricks` package was unavailable in the local environment

This means the repo assessment above is based on:

- code inspection
- contract comparison
- documented behavior
- limited local execution evidence
