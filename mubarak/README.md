# Mubarak — Your README

> Main spec: `../docs/superpowers/specs/2026-04-25-healthcare-multiagent-design.md`
> JSON contracts: `../contracts/`
> Deadline: **19 hours total** from work start (2026-04-25)
> Connections: Mian (Predictor) consumes your specialty output; Tero (Supervisor) calls you

## What you own (revised after agent review — load rebalanced)

| Subfolder | Component | Stack | Phase |
|---|---|---|---|
| `triage/` | TriageAgent — Mosaic AI Knowledge Assistant over symptom→specialty corpus | Python, Knowledge Assistant, Vector Search | 1→2 |
| `transfer/` | **TransferCoordinator (reassigned from Tero)** — UC function + mock 108/ABDM HTTP + FHIR snippet generator + D2D handoff | Python, UC functions, FHIR | 2 |

You also own **integration tests** (E2E) — when Tero swaps mock JSONs in Supervisor with real sub-agent calls (H 16-18), you write the end-to-end test that validates patient flow + doctor flow against the real backend.

Why redistribution: review found Tero at 150% load, you at 40%. FHIR snippet + structured packet generation matches your `Mozzicato/AI-TAX-REFORM` profile (structured output from RAG pipeline).

## What you build

`TriageAgent`: takes free-text symptoms (Hindi or English) → returns specialty + urgency + confidence.

**Stack:**
- Mosaic AI Knowledge Assistant (managed RAG service)
- Vector Search (storage-optimized) — index over symptom→specialty mappings
- Unity Catalog for governance

**Why you:** your `Mozzicato/AI-TAX-REFORM` is a direct analog (RAG over corpus with Python). Knowledge Assistant is Databricks-managed RAG — exactly your profile.

## Schedule (19 hours total — be done by H 11 with Phase 2)

### H 0-1 — workspace access + spike
- [ ] Get Databricks workspace + Unity Catalog perms (Tero provisions)
- [ ] Spike: hello-world Knowledge Assistant in Databricks workspace
- [ ] Confirm Vector Search availability in workspace

### H 1-5 — Phase 1: TriageAgent v1 (4h)
- [ ] Prepare corpus: 5-10 sample symptom→specialty docs (English + Hindi). Examples:
  - "fever + cough + chest pain → respiratory medicine"
  - "बुखार खांसी छाती में दर्द → respiratory medicine"
- [ ] Create Vector Search index (storage-optimized)
- [ ] Configure Knowledge Assistant: prompt template + indexed corpus
- [ ] Smoke test: `triage("fever, chest pain")` → `{specialty: "respiratory medicine", urgency: 3, confidence: 0.84}`
- [ ] **Write `mock_output.json` to your folder immediately** — this unblocks Tero's Supervisor

### H 5-11 — Phase 2: full corpus + Hindi (6h)
- [ ] Expand corpus: full symptom→specialty taxonomy (~50-100 entries)
- [ ] Expand Hindi vocab (Mian/Danish drafts; you review)
- [ ] Urgency scoring (1-5) — add to prompt
- [ ] Confidence calibration — flag low-confidence outputs
- [ ] Smoke test against 20 real-ish patient inputs

### H 11-15 — Phase 2: TransferCoordinator (4h)
- [ ] Create `transfer/` Python package
- [ ] UC function wrapper: input `TransferInput` → output `TransferOutput` (see `contracts/schemas.py`)
- [ ] Mock 108 ambulance dispatch endpoint (FastAPI, returns `ambulance_eta_min` countdown)
- [ ] Mock ABDM record packaging: generate FHIR JSON snippet (use `fhir.resources` Python lib or hand-write)
- [ ] PDF referral packet generator (use `reportlab` or simple HTML→PDF)
- [ ] D2D handoff form generator (returns `d2d_handoff_id`)
- [ ] Smoke test: `pytest tests/transfer_smoke.py` — output validates against `TransferOutput` Pydantic model

### H 15-18 — Integration tests (your second responsibility)
- [ ] Write E2E test in `tests/e2e_patient_flow.py`: full patient flow against real Supervisor + real sub-agents
- [ ] Write E2E test in `tests/e2e_doctor_flow.py`: full doctor flow with TransferCoordinator
- [ ] Help Tero swap mock JSONs in Supervisor with real UC fn calls
- [ ] Pair with Mian on MLflow checkin (your first MLflow exposure)

## Output JSON contracts

You emit two output schemas. Both defined in `../contracts/schemas.py`:

- `TriageOutput` — symptom→specialty result. Mock: `../contracts/triage_output.json`
- `TransferOutput` — receiving hospitals + FHIR + ambulance ETA. Mock: `../contracts/transfer_output.json`

## Input you receive (from Supervisor)

```json
{
  "user_text": "बुखार और छाती में दर्द",
  "language_hint": "hi",
  "context": {"city": "Lucknow"}
}
```

## Dependencies

**Nothing blocks you.** You work fully independently.

**Tero is blocked by you** in Phase 1: Supervisor needs your mock output. **Drop `mock_output.json` in your folder within first 1-2 hours** — that unblocks Tero immediately.

## Risks

- No prior Databricks evidence — pair with Mian on first MLflow checkin (he's working alongside you with MLflow).
- Vector Search is a new primitive. Day -1 spike recommended.

## Smoke test

```bash
cd mubarak/triage
pytest tests/smoke.py
```

Should pass: query "fever Lucknow" returns structured output matching contract.
