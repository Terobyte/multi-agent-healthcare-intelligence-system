# Arushi — Frontend Lead

> **Your job: build a beautiful UI. Nothing else.**
> No backend. No API integration. No Python. No databricks. No SSE wiring.
> You work entirely against **mock JSON files** in `arushi/mocks/`.
> Tero will later swap mock URLs for real endpoints — that's a one-line change.

**Main spec (read once, then forget):** `../docs/superpowers/specs/2026-04-25-healthcare-best-of-merge.md`
**Total time:** ~16 hours

---

## Stack

| Layer | Tech | Why |
|---|---|---|
| Framework | **Vite + React + TypeScript** | Fastest hot-reload at hackathon speed |
| Styling | **Tailwind + shadcn/ui** | Pre-baked beautiful components |
| Map | **Leaflet + react-leaflet** | Free OSM tiles, no token needed |
| Animations | **Framer Motion** | Card flips, pulses, transitions |
| Voice | **Web Speech API** (browser native) | Hindi/English mic input, zero deps |
| Deploy | **Vercel** | `git push` → live URL |
| Mock data | Local JSON in `arushi/mocks/` | Replace with `fetch(API_URL)` in last hour |

**Do NOT install:** axios, redux, react-router-anything-fancy, any state lib bigger than `useState` + `useContext`. Keep it small.

---

## What you build (one app, three surfaces)

```
┌─────────────────────────────────────────────────────────┐
│  HERO — Patient Flow                       [main route] │
│  ┌──────────────────┐  ┌────────────────────────────┐   │
│  │ Chat / mic input │  │ Map (Leaflet, India focus) │   │
│  │                  │  │ 3 hospital pins + dead-zone│   │
│  ├──────────────────┤  │ overlay toggle             │   │
│  │ 3 hospital cards │  └────────────────────────────┘   │
│  │ + trust badges   │  ┌────────────────────────────┐   │
│  │ + Reserve button │  │ Reasoning Panel            │   │
│  └──────────────────┘  │ (live agent tokens stream) │   │
│                        └────────────────────────────┘   │
│  [tab] Doctor Copilot   [tab] NGO Desert Dashboard      │
└─────────────────────────────────────────────────────────┘
```

**Hero rule:** Patient flow is the main page. Doctor copilot + NGO dashboard are **tabs**, not separate routes. One click away.

---

## Components to build (in this order)

### Layer 1 — Patient Flow MVP (4h)

| File | What it does |
|---|---|
| `app/App.tsx` | Root layout: header + 3 tabs (Patient / Doctor / NGO) |
| `app/components/ChatInput.tsx` | Text input + mic button. On submit → loads mock response |
| `app/components/VoiceMic.tsx` | Web Speech API wrapper. Hindi (`hi-IN`) + English (`en-IN`). Pushes transcript to chat |
| `app/components/HospitalMap.tsx` | Leaflet map, India bounds, 3 markers from mock data |
| `app/components/HospitalCard.tsx` | Name, distance, 4 trust badges (bed/oxygen/drug/specialist), Reserve button |
| `app/components/ReasoningPanel.tsx` | Streams mock agent tokens with emoji prefixes (`🩺 triage`, `🔍 validator`, `🗺 router`). Use a `setInterval` to fake stream from `mocks/reasoning_stream.json` |
| `app/components/ReserveModal.tsx` | Confirmation dialog after Reserve click |

### Layer 2 — Killer Visuals (5h)

| File | What it does |
|---|---|
| `app/components/AtomicBookingTiles.tsx` | **The hero animation.** 4 tiles (bed, oxygen, drug, specialist). On Reserve → all 4 flip grey→green with stagger. On rollback → all 4 flash red→grey. Use Framer Motion |
| `app/components/SourceModal.tsx` | Click any trust badge → modal opens. Shows mock MLflow trace JSON with **highlighted source sentence** (yellow background) and **counter-evidence row** (red background) |
| `app/components/DemotedBadge.tsx` | Red "DEMOTED" pill on flagged hospital cards |
| `app/components/ConfidenceInterval.tsx` | Renders `0.94 ± 0.03` next to each trust score |
| `app/components/AgentColorTokens.tsx` | Color-codes streaming reasoning tokens: triage=blue, extractor=purple, validator=red, router=green, transfer=orange |

### Layer 3 — Breadth + Polish (5h)

| File | What it does |
|---|---|
| `app/pages/NGODashboard.tsx` | Tab 2: India PIN map + specialty filter dropdown + click PIN → "0 dialysis within 80km, pop. 4.2M" detail card |
| `app/components/DeadZoneOverlay.tsx` | Toggle button on hero map. ON → red GeoJSON heatmap layer overlays the same map |
| `app/components/GreenPulse.tsx` | "Verified Live" pulsing green dot animation on Tier-1 hospital cards |
| `app/components/OutcomePingReplay.tsx` | Animated sequence: clock → T+2h → SMS bubble → trust factor visibly drops → reputation card-stack ticks down |
| `app/components/StreamTick.tsx` | Pin color shift animation (mock — fires every 30s on a timer for demo) |
| `app/pages/DoctorCopilot.tsx` | Tab 3: sending hospital selector + 3 receivers + referral packet preview + ambulance ETA |
| `submission/README.md` | Project README, architecture diagram screenshot, demo video |

---

## Mock data (everything you need is in `arushi/mocks/`)

Tero will commit these in MVP 0. Until then, **make them up yourself** — the shapes below are the contract.

### `mocks/recommend_response.json` — what you render after chat submit

```json
{
  "request_id": "req_abc123",
  "hospitals": [
    {
      "id": "h_3421",
      "name": "AIIMS Lucknow",
      "lat": 26.85,
      "lon": 80.95,
      "distance_km": 4.2,
      "travel_min": 18,
      "trust": {
        "bed":        { "score": 0.94, "ci": 0.03, "last_verified_min": 2 },
        "oxygen":     { "score": 0.88, "ci": 0.05, "last_verified_min": 4 },
        "drug":       { "score": 0.71, "ci": 0.08, "last_verified_min": 11 },
        "specialist": { "score": 0.92, "ci": 0.02, "last_verified_min": 1 }
      },
      "reputation": 0.86,
      "cost_inr": 12000,
      "demoted": false,
      "tier": 1
    },
    { "id": "h_3422", "name": "KGMU Lucknow",  "lat": 26.87, "lon": 80.92, "distance_km": 6.8, "travel_min": 25, "trust": { "bed": {"score": 0.62, "ci": 0.09, "last_verified_min": 18}, "oxygen": {"score": 0.55, "ci": 0.12, "last_verified_min": 22}, "drug": {"score": 0.48, "ci": 0.14, "last_verified_min": 30}, "specialist": {"score": 0.4, "ci": 0.15, "last_verified_min": 35} }, "reputation": 0.51, "cost_inr": 8500, "demoted": true, "tier": 2 },
    { "id": "h_3423", "name": "Sahara Hospital","lat": 26.83, "lon": 80.99, "distance_km": 9.1, "travel_min": 32, "trust": { "bed": {"score": 0.81, "ci": 0.06, "last_verified_min": 7}, "oxygen": {"score": 0.79, "ci": 0.07, "last_verified_min": 9}, "drug": {"score": 0.83, "ci": 0.05, "last_verified_min": 8}, "specialist": {"score": 0.77, "ci": 0.06, "last_verified_min": 12} }, "reputation": 0.78, "cost_inr": 15000, "demoted": false, "tier": 1 }
  ]
}
```

### `mocks/reserve_success.json` and `mocks/reserve_rollback.json`

```json
// success
{ "confirmed": true,  "atomic_txn_id": "txn_99af", "eta_min": 23, "tiles": ["bed","oxygen","drug","specialist"] }
// rollback
{ "confirmed": false, "rollback_reason": "specialist", "tiles": ["bed","oxygen","drug","specialist"] }
```

When `confirmed: false` → flash all 4 tiles red, then highlight the `rollback_reason` tile in dark red.

### `mocks/reasoning_stream.json` — array of fake agent tokens

```json
[
  { "agent": "triage",     "token": "Detected: chest pain, age 64 → cardiac priority" },
  { "agent": "extractor",  "token": "Pulling roster for AIIMS Lucknow..." },
  { "agent": "validator",  "token": "✓ cardiologist on duty (verified 2 min ago)" },
  { "agent": "validator",  "token": "✗ KGMU: no cardiologist in roster — DEMOTING" },
  { "agent": "router",     "token": "Ranking by trust × reputation × distance" },
  { "agent": "router",     "token": "Top 3: AIIMS, Sahara, KGMU(demoted)" }
]
```

Replay this array with `setInterval(..., 400ms)` — fakes a real SSE stream. Tero swaps in real EventSource later.

### `mocks/trace_response.json` — what SourceModal renders on click

```json
{
  "trust_score_id": "ts_xyz",
  "factor": "specialist",
  "score": 0.4,
  "source_text": "...staff includes 2 general physicians, 1 surgeon, and 4 nurses on rotation...",
  "source_highlight": [40, 49],
  "counter_evidence": { "table": "staff_roster", "row": "no entry for 'cardiologist' in last 30 days" },
  "model": "gpt-4o-mini",
  "timestamp": "2026-04-25T14:23:11Z"
}
```

### `mocks/dead_zones.json` — for NGO dashboard

```json
{
  "pins": [
    { "pin": "201001", "lat": 28.97, "lon": 77.71, "specialty": "dialysis", "count": 0, "nearest_km": 82, "population": 4200000 },
    { "pin": "201002", "lat": 28.95, "lon": 77.69, "specialty": "oncology", "count": 1, "nearest_km": 45, "population": 1800000 }
  ]
}
```

---

## Visual design rules

This is a **demo for ML hackathon judges**. Beauty matters more than features. Apply these:

1. **Dark mode default.** Slate-950 background, slate-100 text, indigo-500 / emerald-500 / rose-500 as accent triad.
2. **Generous whitespace.** Hero page should breathe. No card touches another card.
3. **One animation per second of demo.** Reasoning tokens streaming, tile flips, pin pulses, badge fades — something is always alive.
4. **Trust badges = visual rhythm.** 4 small chips per card with score + tiny confidence number. Color-graded: green > 0.8, yellow 0.5-0.8, red < 0.5.
5. **Map is the visual anchor.** Let it occupy ~40% of hero width. Custom SVG markers, not default Leaflet pins.
6. **Reasoning Panel = chat-like.** Each agent gets a colored left border + monospace font. Timestamp on hover.
7. **Hindi support.** Use Noto Sans Devanagari for Devanagari script. Mic input in Hindi must render correctly.
8. **No emoji in UI text** unless it's the agent prefix (`🩺 🔍 🗺`). Keep professional.

---

## Folder structure

```
arushi/
├── README.md                    ← this file
├── app/                         ← React app root (Vite)
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   ├── index.html
│   └── src/
│       ├── App.tsx
│       ├── main.tsx
│       ├── pages/
│       │   ├── PatientFlow.tsx
│       │   ├── DoctorCopilot.tsx
│       │   └── NGODashboard.tsx
│       ├── components/
│       │   ├── ChatInput.tsx
│       │   ├── VoiceMic.tsx
│       │   ├── HospitalMap.tsx
│       │   ├── HospitalCard.tsx
│       │   ├── ReasoningPanel.tsx
│       │   ├── ReserveModal.tsx
│       │   ├── AtomicBookingTiles.tsx
│       │   ├── SourceModal.tsx
│       │   ├── DemotedBadge.tsx
│       │   ├── DeadZoneOverlay.tsx
│       │   ├── GreenPulse.tsx
│       │   ├── OutcomePingReplay.tsx
│       │   └── StreamTick.tsx
│       ├── lib/
│       │   ├── api.ts           ← single file with all fetch calls; swap mocks→real here
│       │   └── types.ts         ← TS types matching mock JSON shapes
│       └── styles/
│           └── globals.css
├── mocks/                       ← all mock JSON Tero/Mian commit; you build against these
└── submission/                  ← demo video, architecture image, final README
```

---

## API layer (one file, easy to swap)

`app/src/lib/api.ts` — keep all data fetching here.

```ts
const USE_MOCKS = import.meta.env.VITE_USE_MOCKS !== "false";
const BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8000";

export async function recommend(query: string) {
  if (USE_MOCKS) return (await import("../../../mocks/recommend_response.json")).default;
  return fetch(`${BASE}/recommend`, { method: "POST", body: JSON.stringify({ query }) }).then(r => r.json());
}

export async function reserve(hospitalId: string) {
  if (USE_MOCKS) {
    return Math.random() > 0.3
      ? (await import("../../../mocks/reserve_success.json")).default
      : (await import("../../../mocks/reserve_rollback.json")).default;
  }
  return fetch(`${BASE}/reserve`, { method: "POST", body: JSON.stringify({ hospital_id: hospitalId }) }).then(r => r.json());
}

export function streamReasoning(onToken: (t: { agent: string; token: string }) => void) {
  if (USE_MOCKS) {
    import("../../../mocks/reasoning_stream.json").then(m => {
      m.default.forEach((tok, i) => setTimeout(() => onToken(tok), i * 400));
    });
    return () => {};
  }
  const es = new EventSource(`${BASE}/sse`);
  es.onmessage = e => onToken(JSON.parse(e.data));
  return () => es.close();
}
```

That's it. **Tero only needs to set `VITE_USE_MOCKS=false` and `VITE_API_BASE=https://...` in Vercel env.**

---

## Schedule (16 hours)

| Hours | Layer | Deliverable |
|---|---|---|
| H 0–2 | MVP 0 | Vite + Tailwind + shadcn bootstrap, deployed to Vercel, hello-world live |
| H 2–6 | Layer 1 | Patient flow renders 3 cards + map + chat + voice + reasoning panel skeleton |
| H 6–11 | Layer 2 | 4-tile flip animation + click-to-source modal + real-stream colors + DEMOTED badge |
| H 11–16 | Layer 3 | NGO dashboard tab + dead-zone overlay + outcome replay + submission package |

---

## Bootstrap commands

```bash
cd arushi
npm create vite@latest app -- --template react-ts
cd app
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p
npm install leaflet react-leaflet framer-motion lucide-react
npm install class-variance-authority clsx tailwind-merge
npx shadcn-ui@latest init
npx shadcn-ui@latest add button card dialog input tabs badge tooltip
npm run dev
```

For Vercel:

```bash
npm install -g vercel
vercel       # follow prompts, link project
vercel --prod
```

---

## Rules

1. **Never edit anything outside `arushi/`.** All cross-folder data flows through `mocks/` (read-only) or env vars.
2. **All API calls go through `app/src/lib/api.ts`.** No `fetch()` scattered in components.
3. **Don't wait for Tero or Mian.** If a mock is missing, write your own JSON to `mocks/yourthing.json` matching the shapes above. Commit it. They'll match it later.
4. **Ship Layer 1 by H 6, no exceptions.** Layer 2 depends on Layer 1 looking good.
5. **Beautiful > complete.** A polished Patient flow with mock data beats a half-finished 3-tab app.

---

## Smoke test

```bash
cd arushi/app
npm run dev
# open http://localhost:5173
# → patient flow renders 3 cards on map
# → mic button captures Hindi
# → reasoning panel streams agent tokens
# → Reserve button triggers tile flip animation
# → click any trust badge → source modal opens
```

Push to Vercel. Share URL in `#frontend` channel. Done.
