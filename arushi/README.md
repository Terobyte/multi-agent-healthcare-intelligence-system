# Arushi — Your README

> Main spec: `../docs/superpowers/specs/2026-04-25-healthcare-multiagent-design.md`
> JSON contracts: `../contracts/`
> Deadline: **19 hours total** from work start (2026-04-25)
> Connections: you call Tero's Supervisor over HTTPS; you render outputs from all 4 agents

## What you own

| Subfolder | Component | Stack | Phase |
|---|---|---|---|
| `app/` | Databricks App — patient flow + doctor copilot | React + appkit SDK + Leaflet/Mapbox | 1→2→3 |

## What you build

A **single Databricks App** with two surfaces:

1. **Patient flow (Killer A):**
   - Input box (Hindi/English)
   - 3 hospitals on a map with bed predictions
   - Animated "verifying live" banner when Voice MCP fires
   - Confidence band visibly tightens after voice verification (demo theatre)
   - Cost-truth card per hospital (medical + non-medical)

2. **Doctor copilot (Killer B):**
   - Select sending hospital
   - 3 receiving hospital recommendations
   - Referral packet preview (FHIR + PDF)
   - Ambulance ETA countdown with map icon moving
   - Doctor-to-doctor handoff form

**Why you:** your `Managers-pizza` (35 commits, solo TS shipper) + `fitfinder` (community lead) + `ChiPaws` show solo React/TS shipping at hackathon speed. Cursor velocity multiplier confirmed.

**Reuse from `~/Desktop/Projects/Active/ai_hack/hn_dumps/hn5-kit/`:**
- `components/widgets/Map.tsx` (Leaflet + Mapbox)
- `components/widgets/TableView.tsx`
- `components/ChatPanel.tsx`
- Layout grid pattern from `app/(dashboard)/layout.tsx`
- shadcn/ui component patterns

You don't reuse Vercel/Supabase/Next.js routing — those are out. You reuse the **React component code** and adapt to appkit SDK.

## Schedule (19 hours total)

### H 0-1 — workspace access + appkit spike (1h)
- [ ] Get Databricks workspace + UC perms (Tero provisions)
- [ ] Spike: clone https://github.com/databricks/appkit, run hello-world Databricks App locally
- [ ] Confirm appkit React deploy path (`databricks apps deploy`)

### H 1-7 — Phase 1: Patient flow with mock data (6h)
- [ ] Init `app/` with appkit React template
- [ ] Patient flow page: input box + map + 3 hospital cards
- [ ] Wire to Tero's Supervisor mock endpoint (returns hardcoded JSON matching `SupervisorResponse` contract)
- [ ] Map: 3 markers on Lucknow region (Leaflet + OSM tiles fallback if Mapbox token unavailable)
- [ ] Hospital card: name, P(bed) bar, confidence band, travel min, cost
- [ ] Hindi input UTF-8 working

### H 7-13 — Phase 2: Doctor copilot + Voice theatre (6h)
- [ ] Doctor copilot page: sending hospital selector + 3 receivers + packet preview + ambulance ETA
- [ ] **Voice verifying animation:** when `verifying: true` flag in response, show banner + spinner; when verified result arrives, animate confidence band tightening (CSS transition on width)
- [ ] Cost-truth card: medical + non-medical breakdown
- [ ] Toast notifications for "Hospital full", "Doctor unavailable" (this is the Alert agent folded into UI)
- [ ] Wire D2D handoff form

### H 13-16 — Phase 3 demo theatre (3h, pick 1-2)
- [ ] **Genie Space embedded** — chat bar inside dashboard; judge types "ICUs in Pune <30 min" → SQL renders → table populates. **HIGH judge impact**.
- [ ] **Ambulance ETA countdown** — map icon animation moving toward receiving hospital
- [ ] Bridge Doctor Mode (stretch) — D2D shared screen

### H 16-18 — Integration with real Supervisor (2h)
- [ ] Switch from mock endpoint to Tero's real Supervisor URL
- [ ] End-to-end test: Patient flow + Doctor flow against real backend
- [ ] Fix any contract mismatches

### H 18-19 — Pitch + demo polish (1h)
- [ ] **Submission package** — README, demo video edit (your Canva background fits), Devpost-style writeup, GitHub polish. **High-value hidden role.**
- [ ] Slide deck architecture diagram
- [ ] 60-second demo video

## Input you consume (from Supervisor)

```json
{
  "intent": "patient_triage" | "doctor_transfer",
  "verifying": false,
  "hospitals": [
    {
      "id": "h_3421",
      "name": "AIIMS Lucknow",
      "p_bed": 0.72,
      "confidence": 0.65,
      "travel_min": 18,
      "cost_estimate_inr": 12000,
      "non_medical_cost_inr": 4500,
      "lat": 26.85,
      "lon": 80.95
    }
  ],
  "trace_ids": ["tr_abc", "tr_xyz"]
}
```

When Voice MCP fires mid-request, Supervisor sends an SSE event with `verifying: true`, then a final event with updated `confidence` values. Render animation between these states.

## Dependencies

**Nothing blocks you in Phase 1.** Tero gives you a mock Supervisor endpoint within first 2 hours that returns hardcoded JSON.

**Tero needs your URL** for Supervisor integration in Phase 2.

## Reuse map (`hn5-kit` → `app/`)

| `hn5-kit` file | Use as | Notes |
|---|---|---|
| `components/widgets/Map.tsx` | Patient flow map | Drop Leaflet CSS import; keep marker logic |
| `components/widgets/TableView.tsx` | Doctor copilot receivers list | shadcn Table works in appkit |
| `components/ChatPanel.tsx` | Patient input box pattern | Strip SSE complexity, use simple fetch |
| `components/Sidebar.tsx` | Layout shell | Just nav structure, drop auth bits |
| Tailwind config | Same | Keep |
| shadcn components | Same | Keep button/card/input/dialog/sheet/tabs/sonner |

You don't use: Supabase auth, RLS, middleware, ingest API routes, openai client.

## Risks

- appkit SDK is new (2025-2026) — docs may be thin. H 0-1 spike critical.
- No Python/ML evidence — don't get pulled into backend work. Stay in `app/`.
- Time zone: confirm 19h overlap with team's core hours.

## Smoke test

```bash
cd arushi/app
npm run dev
# open localhost:8080 (or appkit default port)
# patient flow renders with 3 mock hospitals; doctor flow renders with mock referral packet
```
