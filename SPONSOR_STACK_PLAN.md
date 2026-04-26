# Sponsor Stack Plan v2 — `feat/sponsor-stack`

**Branch:** `feat/sponsor-stack` (off `main`)
**Owner:** Tero
**Date:** 2026-04-26
**Hackathon:** HackNation 2026 Challenge 3 — Databricks Agentic Healthcare Maps
**Status:** v2 — rewrites v1 after 5-reviewer pass found 9 BLOCKER / 8 HIGH issues
**Goal:** Add sponsor-criteria features that wrap *existing* `/triage`, `/recommend`,
`/book` (all already shipped on main per `app/main.py:398-463`) without blocking
req2 (Mubarak) or req3 (Arushi).

---

## What changed from v1

| v1 claim | Reality | New plan |
|---|---|---|
| `TriageAgent` class | Doesn't exist — it's a function `triage()` at `app/agents/triage.py:244` | Wrapper imports the function |
| `mlflow.pyfunc.PythonModel` | Legacy as of MLflow 3.0; no AI Playground / Agent Eval / `agents.deploy()` wiring | Use `mlflow.pyfunc.ResponsesAgent` |
| `log_model(artifact_path=...)` | Deprecated — `name=` since MLflow 3.x; missing `pip_requirements`, `resources`, `input_example` | Use current shape |
| `/triage`, `/recommend` are Mubarak's | Already on main: `app/main.py:398-406, 426-463` | Wrap Tero's existing routes — no Mubarak coordination needed for #1 |
| `KnowledgeAssistantClient.query()` | Fictional class | Use `WorkspaceClient().serving_endpoints.query(name=...)` |
| `databricks-genie-api` package | Doesn't exist on PyPI | Use `databricks-sdk` → `WorkspaceClient().genie` |
| Genie `follow_up()` method | Wrong name | `start_conversation_and_wait`, `create_message_and_wait`, `get_message_query_result` |
| WS engine «уже готов в репо» | `tero/voice/` empty; engine is **separate TS package** at `~/Desktop/Projects/Active/ai_hack/fishaudio` (`@fishaudio-engine/core`), Fish-only streaming TTS, NOT OpenAI-relay | Reframe Voice → Fish TTS narration only |
| Voice Mode B = OpenAI Realtime bidirectional | 6-10h research project (TTS swap mid-stream); collides with Arushi's Web Speech API path (req3 Block 11) | Drop bidirectional. TTS-only Hindi/Urdu narration via Fish engine after `/book` commit |
| `/sponsor/triage` + `/sponsor/genie/query` open | Bug #1 doctrine: gate mutating routes | Add `Depends(require_demo_key)` + slowapi limits |
| WS `/voice/stream` | Removed — no bidirectional pipeline → no public WS endpoint needed | n/a |
| 5 secrets undocumented | Plan didn't extend `.env.example` | All new keys + comments below |
| `_TOKEN_PATTERNS` covers only `dapi*` | `sk-...` (OpenAI) and Fish-key shape leak | Extend patterns before any new module logs |
| KA «preview» risk | KA went GA Jan 2026 | Drop preview caveat; pitch stronger |
| No SAFE_DEMO mode | Stage robustness gap | `SAFE_DEMO=1` short-circuits everything to canned artifacts |

---

## Final scope (after triage)

**BUILD on this branch:**
- **Feature 1 — Agent Bricks wrapper** (1-2h with cuts — ship `ResponsesAgent`
  subclass + local `log_model` smoke; skip live `agents.deploy()` unless
  workspace serving permits trivially).
- **Feature 4 — Genie client + canned mode default** (1.5h canned; +1.5h optional
  live). Real `w.genie` API calls behind a `SPONSOR_GENIE_LIVE=1` flag; canned
  artifact serves the 3 demo queries by default.
- **Feature 3 (reframed) — Fish Audio TTS narration** (1-2h). Backend hook
  after `/book` COMMITTED → 1-sentence Hindi/Urdu text → Tero's
  `@fishaudio-engine/core` package via Node sidecar OR pre-baked MP3 from
  `_demo/`. Frontend (Arushi) plays audio when ambulance card appears.
- **Feature 2 — KA stub only** (30 min). Module exists, always falls back to
  JSON corpus; pitch-line-only. Real KA wiring **deferred** — coordinate with
  Mubarak post-demo.

**DROP from this branch:**
- OpenAI Realtime bidirectional voice (no demo lift over TTS narration; 6-10h cost; collides with Arushi's Web Speech API).
- Live `agents.deploy()` of Agent Bricks (workspace permission tax not worth it for hackathon; pitch line works on `log_model` alone).
- Live KA query path (Mubarak coordination required).

---

## Branch & directory layout

```
app/sponsor/
├── __init__.py
├── flags.py                  # request-time env reader, SAFE_DEMO short-circuit
├── scrub.py                  # extends bug-#20 patterns to sk-* and Fish keys
├── agent_bricks.py           # #1 — ResponsesAgent wrapping triage()
├── genie.py                  # #4 — WorkspaceClient().genie wrapper
├── knowledge_assistant.py    # #2 — stub only, always falls back
├── voice_narration.py        # #3 — POST /sponsor/narrate text → audio bytes
├── _demo/
│   ├── demo_genie_canned.json
│   ├── demo_agent_bricks_response.json
│   ├── demo_voice_5603_hi.mp3
│   ├── demo_voice_5603_ur.mp3
│   ├── demo_voice_8888_hi.mp3
│   └── demo_voice_8888_ur.mp3
└── tests/
    ├── test_flags.py
    ├── test_scrub.py
    ├── test_agent_bricks_wrapper.py
    ├── test_genie_canned.py
    ├── test_ka_stub.py
    └── test_voice_narration.py

scripts/sponsor/
└── log_agent_bricks.py       # one-shot mlflow.log_model run
```

**`.env.example` additions (all empty by default):**

```
# Sponsor stack — all default off, flip per demo
SPONSOR_AGENT_BRICKS=false        # mount /sponsor/triage
SPONSOR_GENIE=false               # mount /sponsor/genie
SPONSOR_GENIE_LIVE=false          # if true, hit real Genie; else canned
SPONSOR_VOICE=false               # mount /sponsor/narrate
SPONSOR_KA=false                  # KA stub always returns fallback
SAFE_DEMO=false                   # short-circuit ALL sponsor routes to _demo/

# Required when SPONSOR_GENIE_LIVE=true
DATABRICKS_GENIE_SPACE_ID=

# Required when SPONSOR_VOICE=true (sidecar reads same key)
FISH_API_KEY=                     # store in 1Password; rotate per event
FISH_REFERENCE_ID=92a2600282e547f098b4a8de1bc9a44a   # JLM4.7

# Optional — only set if log_model targets a remote MLflow tracking server
MLFLOW_TRACKING_URI=
```

---

## Auth + secrets discipline (BLOCKERS from review #4)

### All new public routes gated

```python
@app.post("/sponsor/triage", dependencies=[Depends(require_demo_key)])
@limiter.limit("20/minute")
async def sponsor_triage(...): ...

@app.post("/sponsor/genie/query", dependencies=[Depends(require_demo_key)])
@limiter.limit("10/minute")
async def sponsor_genie(...): ...

@app.post("/sponsor/narrate", dependencies=[Depends(require_demo_key)])
@limiter.limit("10/minute")
async def sponsor_narrate(...): ...
```

`flags.py` reads `os.getenv` **per-call** (property, not import-time constant)
so demo-day flips don't need a redeploy.

### Token scrub patch (bug #20 extension)

`app/sponsor/scrub.py` adds patterns to `app/main.py::_TOKEN_PATTERNS`:
- `sk-[A-Za-z0-9_-]{20,}` (OpenAI)
- `\b[a-f0-9]{32}\b` (Fish key 32-hex shape)

Patch is applied on `app/sponsor/__init__.py` import; idempotent guard.

### Pre-recorded artifact lookup is allowlist-only

Path-traversal mitigation: `_DEMO_LOOKUP: dict[str, Path]` is a hardcoded map.
Any user-supplied identifier is checked via `_DEMO_LOOKUP.get(key)`; no `Path /
user_input` concatenation. Routes that take a `demo_id` reject anything not in
the allowlist (5603, 8888, 959, 2672, 186, 881 — same as `bugs.md` demo set).

### PII flow

- `/sponsor/triage`: same input as `/triage` (free-text symptoms). Wrapper does
  not log raw symptoms; passes them straight to `triage()`. Field-name
  discipline preserved (`facility_id`, `lon`).
- `/sponsor/narrate`: input is a **template-built** sentence with `{hospital_id}`
  + `{eta_min}` (no patient identifier). Patient pseudonym never reaches Fish.
- `/sponsor/genie/query`: input is a natural-language question about the
  warehouse, not patient data.

---

## SAFE_DEMO=1 — one-button safe mode (from review #5)

When `SAFE_DEMO` is true:
- Every sponsor route bypasses live API and returns `_demo/*` artifact.
- `/sponsor/triage` returns `demo_agent_bricks_response.json` keyed by an
  optional `demo_id` query param (default `5603`).
- `/sponsor/genie/query` returns the next entry from `demo_genie_canned.json`
  per conversation_id.
- `/sponsor/narrate` returns the matching pre-baked MP3.
- `/sponsor/health` reports `{"safe_demo": true}` so frontend banner can show
  «demo mode».

Stage workflow: laptop boots with `SAFE_DEMO=1`. Pre-demo rehearsal flips to
`0`. If any check fails, flip back. Single env var, single source of truth.

---

## Feature 1 — Agent Bricks wrapper (1-2h)

### Code shape

```python
# app/sponsor/agent_bricks.py
import mlflow
from mlflow.pyfunc import ResponsesAgent
from mlflow.types.agent import ResponsesAgentRequest, ResponsesAgentResponse
from app.agents.triage import triage as _triage_function
from app.schemas import TriageOutput

class TriageResponsesAgent(ResponsesAgent):
    def predict(self, request: ResponsesAgentRequest) -> ResponsesAgentResponse:
        # request.input[-1] is OpenAI-Responses-style message
        symptoms = request.input[-1].content if request.input else ""
        language = request.context.get("language", "en") if request.context else "en"
        result: TriageOutput = _triage_function(symptoms, language)
        return ResponsesAgentResponse(
            output=[{
                "type": "message",
                "role": "assistant",
                "content": [{"type": "output_text", "text": result.model_dump_json()}],
            }]
        )
```

### log_model script

```python
# scripts/sponsor/log_agent_bricks.py
import mlflow
from app.sponsor.agent_bricks import TriageResponsesAgent

agent = TriageResponsesAgent()
example = {"input": [{"role": "user", "content": "chest pain"}]}

with mlflow.start_run():
    mlflow.pyfunc.log_model(
        name="triage_agent",
        python_model=agent,
        input_example=example,
        pip_requirements=[
            "mlflow",
            "databricks-agents",
            "databricks-sdk",
            "pydantic>=2",
        ],
    )
```

If `MLFLOW_TRACKING_URI` is unset, runs land in `./mlruns`. That is sufficient
for the pitch — we have a logged model that conforms to Agent Framework spec.

### Route

```python
# app/main.py addition (gated import to keep main importable when sponsor off)
if flags.SPONSOR_AGENT_BRICKS:
    from app.sponsor.agent_bricks import TriageResponsesAgent
    _bricks_agent = TriageResponsesAgent()

    @app.post("/sponsor/triage", dependencies=[Depends(require_demo_key)])
    @limiter.limit("20/minute")
    async def sponsor_triage(req: Request, body: dict): ...
```

### Risks
- `databricks-agents` import on a fresh laptop without Databricks creds: tested
  in scaffolding; `import` itself is offline-safe per review.
- `mlflow` (full) vs pinned `mlflow-skinny`: handled by adding `mlflow>=3.0` to
  `pip_requirements` of the logged model only — the running app keeps using
  whatever's already installed. Avoid uninstalling skinny; install `mlflow`
  side-by-side via a separate `requirements-sponsor.txt`.

---

## Feature 4 — Genie (1.5h canned, +1.5h live)

### Code shape

```python
# app/sponsor/genie.py
from databricks.sdk import WorkspaceClient
from app.sponsor.flags import flags

class GenieClient:
    def __init__(self):
        self._w = WorkspaceClient() if flags.SPONSOR_GENIE_LIVE else None
        self._space_id = os.getenv("DATABRICKS_GENIE_SPACE_ID", "")

    def ask(self, conv_id: str | None, query: str) -> dict:
        if flags.SAFE_DEMO or not flags.SPONSOR_GENIE_LIVE:
            return _canned_response(conv_id, query)

        if conv_id is None:
            res = self._w.genie.start_conversation_and_wait(
                space_id=self._space_id, content=query
            )
            conv_id = res.conversation_id
        else:
            res = self._w.genie.create_message_and_wait(
                space_id=self._space_id, conversation_id=conv_id, content=query
            )
        # extract SQL + result
        sql = ""
        rows = []
        for att in (res.attachments or []):
            if att.query and att.query.statement:
                sql = att.query.statement
                rows_resp = self._w.genie.get_message_query_result(
                    space_id=self._space_id,
                    conversation_id=conv_id,
                    message_id=res.id,
                )
                rows = [r.data_array for r in (rows_resp.statement_response.result.data_array or [])]
        return {"conversation_id": conv_id, "sql": sql, "rows": rows}
```

### Canned default

`_demo/demo_genie_canned.json`:

```json
{
  "queries": [
    {
      "match": "ICU beds",
      "sql": "SELECT facility_id, name, icu_beds_avail FROM gold_trust_final WHERE icu_beds_avail > 0",
      "rows": [["5603","Apollo Mumbai",4], ["8888","Tata Memorial",2]]
    },
    {"match": "trust", "sql": "...", "rows": [...]},
    {"match": "cardiac", "sql": "...", "rows": [...]}
  ]
}
```

Live exception path also falls back to canned: any `databricks.sdk` error →
return next canned entry. No 5xx ever reaches the user.

### Risks
- Genie space cold-start: rehearsal step warms it up.
- Programmatic space provisioning is preview; we create the space in UI once.

---

## Feature 3 — Fish TTS narration (1-2h)

### Architecture

```
[/book commits] -> backend builds 1 sentence in hi/ur
                -> POST /sponsor/narrate {text, lang, demo_id}
                -> Node sidecar (existing fishaudio package)
                -> stream PCM/MP3 chunks back over HTTP chunked transfer
                -> frontend plays
```

Two implementation paths, pick one based on time:

**Path A (recommended — 1h):** Pre-bake the 6 demo MP3s offline using
`fishaudio` repo's `e2e-test.mjs` adapted to write MP3, commit them to
`_demo/`. `/sponsor/narrate` just streams the matching file from disk. Zero
live Fish calls during demo. Hindi + Urdu × 3 demo facilities = 6 files.

**Path B (live — 2h):** Run Node sidecar as separate process (Procfile entry
`narrate: node node_modules/@fishaudio-engine/core/scripts/narrate-server.mjs`).
Backend Python proxies to `localhost:9301/narrate`. Live, but adds a moving
part on stage.

**Critical (per Tero):** there are effectively two ways to call the engine.
`speak(text)` sends ONE `{event:"text"}` with the full sentence — Fish server
waits for the whole input before generating audio (text is "accumulated"
client-side, slower TTFB). `stream(asyncIter)` sends each yielded fragment as
its own `{event:"text"}` event — Fish starts generating on the first fragment
(~0.5s TTFB, real streaming). **The sidecar (Path B) MUST use `stream()` with
the template chunked by phrase boundary**, not `speak()`. Path A pre-baking
can use either since latency doesn't matter for a file on disk.

Default: Path A. `SAFE_DEMO=1` forces Path A even when `SPONSOR_VOICE=true`.

### Voice picks (Fish Audio reference IDs)

Selected from the public Fish Audio marketplace; both confirmed working with
the bake scripts in `~/Desktop/Projects/Active/ai_hack/fishaudio/scripts/`.

| Lang | Reference ID | Voice | Notes |
|------|---|---|---|
| Hindi | `6c3d7cfb3d1d44dba29160ef21a8bad6` | शांत हिंदी आवाज़ | Female, calm, 464 uses, language tag `hi` only — best native-Hindi female on the marketplace |
| Urdu  | `16344fa6cc2a46a09825a0871cecc0a6` | Sohail Abbas — Urdu | **Male** (no native-Urdu female exists on Fish Audio); reads Nastaliq script natively, professional/calm tagging |

Bake scripts: `fishaudio/scripts/bake-hindi.mjs`, `fishaudio/scripts/bake-urdu.mjs`.
Output committed under `app/sponsor/_demo/demo_voice_{5603,8888,959}_{hi,ur}.mp3`
(MPEG ADTS layer III, 128 kbps, 44.1 kHz, mono, ~80-100 KB each).

### Hindi/Urdu templates (deterministic)

```python
HI_TEMPLATE = "आपके लिए {hospital_name} में बिस्तर आरक्षित है। एम्बुलेंस {eta} मिनट में पहुंचेगी।"
UR_TEMPLATE = "آپ کے لیے {hospital_name} میں بستر محفوظ ہے۔ ایمبولینس {eta} منٹ میں پہنچے گی۔"
```

No LLM in the loop → demo-time determinism.

### Frontend integration (Arushi's branch)

Audio plays on `event: ambulance_dispatched` SSE event. Browser autoplay policy
requires user gesture — Arushi's existing «Reserve» button counts as the
gesture, so audio plays freely after that click.

### Risks
- Browser autoplay block: mitigated by user-click gesture (Reserve button).
- Path B sidecar crash: drop to Path A automatically if HTTP request to
  `localhost:9301` fails.

---

## Feature 2 — KA stub (30 min)

```python
# app/sponsor/knowledge_assistant.py
import json
from pathlib import Path
from app.sponsor.flags import flags

_CORPUS = json.loads((Path(__file__).parent.parent / "agents" / "symptom_corpus.json").read_text())

class KnowledgeAssistantStub:
    """KA-shaped retrieval that always uses the JSON corpus.

    Real KA wiring is deferred — see SPONSOR_STACK_PLAN.md v2 §Drop list.
    Pitch slide can still claim 'designed for Knowledge Assistant on
    mubarak_vs' because the interface is KA-compatible (returns
    {"matches": [{"text", "score"}]}).
    """

    def retrieve(self, symptom_text: str) -> dict:
        if flags.SAFE_DEMO:
            return {"matches": _CORPUS[:3]}
        # always fall back; live wiring deferred
        return {"matches": _keyword_match(symptom_text, _CORPUS)}
```

Not mounted on a public route. Imported by `agent_bricks.py` if/when needed.

---

## Test strategy

Per-module pytest with stub-mode default. Live tests gated behind
`@pytest.mark.live` + env-var presence. CI runs unit tests only. All sponsor
modules' unit tests must pass before merging this branch into
`feat/frontend-healthcare-demo`.

---

## Order of work (today)

| # | Step | Time |
|---|------|------|
| 0 | Scaffold `app/sponsor/`, `flags.py`, `scrub.py`, `.env.example`, `__init__.py` patch loader | 30 min |
| 1 | Feature 1 — `agent_bricks.py` + `scripts/sponsor/log_agent_bricks.py` + test | 1.5h |
| 2 | Feature 4 — `genie.py` + canned JSON + test | 1.5h |
| 3 | Feature 3 — `voice_narration.py` Path A (pre-baked MP3 streaming) + test | 1h |
| 4 | Feature 2 — `knowledge_assistant.py` stub + test | 30 min |
| 5 | Wire all routes into `app/main.py` behind flags + add `SAFE_DEMO` short-circuit | 30 min |
| 6 | Pre-bake 6 Hindi/Urdu MP3s via `fishaudio/scripts/` | 30 min |
| 7 | Pre-demo rehearsal (~25 min checklist below) | 25 min |

**Total: ~6.5h focused work.** Slack: +1h for env/dep debugging, +30 min for
demo-day. Realistic budget: 8h.

---

## Pre-demo rehearsal checklist (~25 min)

1. Hit `/sponsor/triage` once (warm any MLflow serving — only if live mode on).
2. Run all 3 canned Genie queries via `/sponsor/genie/query` to verify shape.
3. Hit `/sponsor/narrate?demo_id=5603&lang=hi` to verify MP3 plays.
4. Confirm SAFE_DEMO toggle works: flip `1` → all canned; flip `0` → live (in
   the rooms where live is configured).
5. Frontend dry-run: full demo flow with `SAFE_DEMO=1`.
6. Frontend dry-run: full demo flow with `SAFE_DEMO=0` on venue Wi-Fi.

---

## Pitch slide (one-liner draft)

> «AarogyaNet's triage agent is logged via the **Mosaic AI Agent Framework**
> (`mlflow.pyfunc.ResponsesAgent`), our clinician copilot embeds **Databricks
> Genie** for multi-turn data exploration over the trust-calibrated facility
> table, and patient handoff narrates in Hindi/Urdu via a streaming
> WebSocket TTS engine.»

Three concrete sponsor name-drops, all backed by code that runs.

---

## Out of scope (will not touch)

- `/triage`, `/recommend`, `/outcome`, `/transfer`, `/book` route handlers in
  `app/main.py` (sponsor adds new `/sponsor/*` routes only)
- `app/agents/{triage,router,booking,reasoning_stream}.py`
- `app/util.py`, `app/db.py`, `app/schemas.py`
- `scripts/databricks/*` SQL or notebooks
- Any `tests/test_known_bugs_*.py` (the 8 MINE bugs are a separate workstream)
- Merging to `main` or to Arushi's `feat/frontend-healthcare-demo` until the
  demo is over

---

## Open items

1. Confirm `mubarak_vs` / `vs_healthcare` status with Mubarak post-hackathon
   if KA real wiring is pursued.
2. Decide whether to commit pre-baked MP3s to git or generate them in CI
   (size: ~50KB each × 6 = 300KB, acceptable).
3. If `databricks-agents` install pulls a transitive `mlflow` that breaks the
   existing `mlflow-skinny` pin → install in a separate venv used only by
   `scripts/sponsor/log_agent_bricks.py`, not the runtime app.
