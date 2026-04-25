# PLAN — what's left to build

> Authoritative todo list. The original spec (`docs/superpowers/specs/2026-04-25-healthcare-best-of-merge.md`) is now reference architecture — completed items removed from active todos.

## ✅ DONE — Data Layer (this is the foundation, do NOT redo)

| Component | Status | Owner | Where |
|---|---|---|---|
| Bronze: VF dataset (10000 × 41) | ✅ | Tero | `workspace.default.vf_hackathon_dataset_india_large` |
| Silver: cleaned + parsed JSON arrays | ✅ | Danish | `workspace.default.silver_facilities` |
| Gold: rule-based trust + 4 factor proxies (10000) | ✅ | Tero | `workspace.default.gold_trust_rules` |
| Gold: NGO Desert Map per PIN (3736) | ✅ | Tero | `workspace.default.gold_pin_capabilities` |
| Gold: LLM TrustScorer (Llama 3.3 70B, 256 hospitals) | ✅ | Mubarak | `workspace.default.gold_trust_llm` |
| Gold: Validator second-pass (Llama 4 Maverick, 255) | ✅ | Mubarak | `workspace.default.gold_trust_llm_v2` |
| Gold: Two-model agreement table | ✅ | Mubarak | `workspace.default.gold_trust_two_model` |
| Gold: Final hybrid trust (4-tier badge) | ✅ | Tero | `workspace.default.gold_trust_final` |
| Atomic Booking: 5-table saga schema (txn + bed + ambulance + doctor + drug) | ✅ | Tero | `workspace.default.txn_atomic`, `bed_reservations`, `ambulance_dispatches`, `doctor_slots`, `drug_reservations` |
| Outcome feedback append-only ledger | ✅ | Mubarak | `workspace.default.outcome_feedback` |
| v_agent_reputation view | ✅ | Mubarak | view |
| v_trust_calibrated view (with visible cap-firing demo arc) | ✅ | Mubarak | view |
| v_committed_bookings view | ✅ | Tero | view |
| Vector Search endpoint `vs_healthcare` (ONLINE) | ✅ | Tero | embedded ~250/10000 (provisioning slow on Trial) |
| Demo seed (5 atomic bookings + 1 rollback + 18 outcomes) | ✅ | Arushi | inserted |
| Smoke test 7/7 passing | ✅ | Tero | `scripts/databricks/smoke_test.py` |
| Demo runbook (5-min walkthrough) | ✅ | Tero | `docs/DEMO-RUNBOOK.md` |
| Reproducible rebuild scripts (00→10) | ✅ | Tero | `scripts/databricks/` |

**Demo anchors live in Databricks now:**
- INHS Sanjivani Kochi — two-model-verified, trust 0.888, 6 outcomes confirm → calibrated 0.888
- **Aradhna Super Speciality — two-model-verified 0.831, 6 outcomes contradict → calibrated 0.350 (cap drops by 0.481, visible self-correction)**
- Bihar 149 PINs zero oncology, 130 zero emergency
- 80 hospitals two-model-verified / 169 models-disagree / 13 single-model / 9738 rule-inferred

---

## 🔨 TODO — Application Code (this is what's left)

### P0 — Killer demo (must work before pitch)

| # | Component | Owner | ETA | Spec ref | Notes |
|---|---|---|---|---|---|
| A1 | **FastAPI app skeleton** — `main.py` with CORS, health, settings reading from env | Tero | 30 min | §3.1 | Reads `DBX_PROFILE`, `DBX_WH`, `OPENAI_API_KEY` |
| A2 | **schemas.py** — 6 Pydantic models: `Hospital`, `TrustScorerOutput`, `TransferCoordOutput`, `IntakeHandshake`, `OutcomeFeedback`, `ReasoningPanelEvent` | Tero | 30 min | §7 Integration Contracts | Wire to existing Databricks columns |
| A3 | **TriageAgent** — `POST /triage` symptom→specialty (BGE keyword fallback while VS finishes embedding) | Mubarak | 1 h | §3.2 | Hits `silver_facilities` via SQL warehouse |
| A4 | **RouterAgent** — `POST /recommend` returns top 3 ranked by trust × distance × specialty match | Mubarak | 1 h | §3.5 | Reads `gold_trust_final` + `v_trust_calibrated` |
| A5 | **BookingAgent (Supervisor) + saga `book_atomic()`** — 4-way insert across `bed/ambulance/doctor/drug`, ROLLED_BACK on any fail | Tero | 1.5 h | §3.1 + §3.6 | Returns `transaction_id` + per-resource status |
| A6 | **/outcome POST** — patient ping endpoint that appends to `outcome_feedback` | Mubarak | 20 min | §3.11 | Hashes `patient_id` |
| A7 | **Frontend** — Patient flow (symptom → 3 hospitals → book) + trust badge component + outcome ping | Arushi | 4-5 h | §3.15 | In progress per Arushi |

### P1 — Rubric anchors (Discovery / IDP / Social Impact)

| # | Component | Owner | ETA | Spec ref |
|---|---|---|---|---|
| B1 | **Validator Agent** Python wrapper around `gold_trust_two_model` for live API responses | Mubarak | 30 min | §3.14 |
| B2 | **NGO Desert Dashboard** UI — heatmap from `gold_pin_capabilities` | Arushi | 2 h | §3.13 |
| B3 | **Live Agent Reasoning Panel** SSE — stream agent thoughts from FastAPI | Tero | 1.5 h | §3.10 |
| B4 | **Click-to-source modal** — show `llama_3_3_reasoning` + `llama_4_reasoning` from `gold_trust_final` | Arushi | 1 h | §4 |

### P2 — Wow tier (only if P0 + P1 green)

| # | Component | Owner | ETA | Spec ref |
|---|---|---|---|---|
| C1 | **Voice input** (Whisper or browser SpeechRecognition) | Arushi | 1 h | §3.9 |
| C2 | **Synthetic Live Stream** — generate ambulance/bed events to demo "live system" | Tero | 1 h | §3.8 |
| C3 | **Mosaic AI Agent Framework wrapper** — `databricks.agents.register` over BookingAgent for "we use Agent Bricks" pitch | Tero | 1-2 h | Layer 4 |
| C4 | **Transfer Copilot (Doctor tab)** — referral packet RAG | Mubarak | 2 h | §3.5, §5 |

---

## 🟡 KNOWN minor cleanup (post-demo)

- Vector Search index still embedding (Trial slow); keyword fallback in TriageAgent works today
- `dbq.py` SQL injection: dev tool only, low risk for hackathon
- Hardcoded warehouse ID: env var override added, safe enough
- Telegram token in user's global CLAUDE.md (NOT in our repo)

---

## Critical path to demo

```
H 0-1  : A1 (FastAPI skeleton) + A2 (schemas)              ← Tero
H 1-3  : A3 (Triage) + A4 (Router) + A6 (Outcome)          ← Mubarak  
H 1-5  : A7 (Frontend patient flow)                         ← Arushi
H 3-5  : A5 (Booking saga)                                  ← Tero
H 5-7  : End-to-end smoke (UI → API → Databricks → UI)     ← all
H 7-13 : P1 anchors (B1-B4)
H 13-19: P2 wow + dry-run pitch
```

Smoke gate at H 7: patient says "chest pain in Bihar" → 3 hospitals show with trust badges → book → outcome ping → reputation cap fires for next patient. If this works, demo is safe.
