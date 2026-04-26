# bugs.md

Triage of the 21-finding report from a 10-agent review pass. Each finding is
classified `MINE`, `SCOPE` (belongs to a teammate per requirements), `DISMISSED`
(I stand by the original design choice), or `INVALID` (reviewer was wrong).

For every `MINE`, a failing test is added to `tests/test_known_bugs_saga.py`
or `tests/test_known_bugs_sse.py` so the bug stays visible until fixed.

Last updated: 2026-04-25.

## CRITICAL

| # | Bug | File | Triage | Failing test |
|---|-----|------|--------|--------------|
| 1 | DEMO_KEY auth open by default — empty env var = anyone can POST `/book` | `app/main.py:58` | **MINE** — by-design for local dev, but Render-side risk if env unset | `test_bug1_demo_key_unset_must_reject_unauthenticated_post` |
| 2 | 4 routes missing: `/triage`, `/recommend`, `/outcome`, `/transfer` | `app/main.py` | **SCOPE** — Mubarak (A2-A4) + Arushi (A7) per `team.md` | n/a |
| 3 | `hash_patient_id` not called in `/book` — Block 35d says "apply in Block 21 booking parent INSERT" but raw patient_id flows through | `app/agents/booking.py` | **MINE** — created the helper, never wired it | `test_bug3_raw_patient_id_must_not_reach_warehouse_params` |

## HIGH

| # | Bug | File | Triage | Failing test |
|---|-----|------|--------|--------------|
| 4 | PII salt fallback "aarogyanet-dev-salt-do-not-use-in-prod" silently used when `PII_SALT` unset | `app/util.py:15` | **MINE** — should fail-loud in non-dev | `test_bug4_dev_salt_must_not_be_used_silently` |
| 5 | SSE heartbeat doesn't fire every 15s — only triggers when an agent step takes >15s. Render/Cloudflare idle-close after 30-60s | `app/main.py:185` | **MINE** — softened the docstring instead of fixing impl | `test_sse_heartbeat_must_fire_within_15s_when_agent_step_long` |
| 6 | Race: dup-active-txn SELECT not atomic with parent INSERT | `app/agents/booking.py:54-58` | **MINE** (re-opened) — dismissed earlier as "single-user demo" but user disagrees | `test_bug6_concurrent_book_atomic_must_not_double_commit` |
| 7 | Empty `results` dict passes `all(v == "OK")` (vacuous truth) | `app/agents/booking.py:111` | **INVALID** — already guarded by `len(results) == len(RESOURCE_TABLES)` since commit `1a44278` | n/a |
| 8 | SSE `event: done` payload doesn't match contract — Block 33 spec says full `RecommendResponse` JSON, code emits `{session_id, trace_id}` | `app/main.py:188` | **MINE** — `RecommendResponse` schema doesn't even exist yet | `test_sse_done_event_must_carry_recommend_response_payload` |
| 9 | Block 30 smoke gate inevitably red — calls `/triage`, `/recommend`, `/outcome` which don't exist | `requirements.md` | **SCOPE** — same as #2 | n/a |

## MEDIUM

| # | Bug | File | Triage | Failing test |
|---|-----|------|--------|--------------|
| 10 | Rate limiting not on `/outcome` | `app/main.py` | **SCOPE** (route doesn't exist) | n/a |
| 11 | Demo key auth not on `/outcome` | `app/main.py` | **SCOPE** | n/a |
| 12 | `stream_endpoint` in `reasoning_stream.py` is dead code | `app/agents/reasoning_stream.py` | **DISMISSED** — built ahead of need so Mubarak's agents can import it | n/a |
| 13 | No cleanup on SSE client disconnect — generator runs to completion even when client gone | `app/main.py:170-192` | **MINE** (re-opened) — trivial to fix with `request.is_disconnected()` | `test_sse_must_abort_on_client_disconnect` |
| 14 | `/sse_demo` returns JSON HTTPException 503 when transcript missing — breaks SSE contract | `app/main.py:204-205` | **MINE** — should emit `event: error` then close, not raise | `test_sse_demo_missing_transcript_must_emit_sse_error_not_503` |
| 15 | `CORS allow_origins=["*"]` — any domain can hit the API | `app/main.py:42` | **DISMISSED** — fine for hackathon Render URL | n/a |
| 16 | `VS_ENDPOINT` documented in Block 11 but missing from `.env.example` | `.env.example` | **INVALID** — line 5 already has `VS_ENDPOINT=mubarak_vs`. Reviewer hallucinated. | n/a |
| 17 | Active-txn check filters `IN ('RESERVED','COMMITTED')`, doesn't include `EXPIRED` | `app/agents/booking.py:56` | **INVALID** — `EXPIRED` txns should NOT block new bookings | n/a |
| 18 | `tests/test_util.py` missing | `tests/` | **INVALID** — file exists since commit `7db360d` (5 tests passing) | n/a |

## LOW

| # | Bug | File | Triage | Failing test |
|---|-----|------|--------|--------------|
| 19 | Extra `commit_error` field in `BookingOutput` not in Block 14 spec | `app/schemas.py:44` | **DISMISSED** — added to satisfy round-1 reviewer feedback | n/a |
| 20 | `exc_info=True` could leak token in Databricks SDK stack trace | `app/main.py:102` | **MINE** | `test_bug20_exception_log_must_not_leak_databricks_token` |
| 21 | `STATEMENT_TIMEOUT=30` hardcoded in `app/db.py` | `app/db.py:23` | **DISMISSED** — fine as default | n/a |

## Summary

- **MINE (8 real defects):** #1, #3, #4, #5, #6, #8, #13, #14, #20 → 9 failing tests across `tests/test_known_bugs_saga.py` (5) + `tests/test_known_bugs_sse.py` (4)
- **SCOPE (4):** #2, #9, #10, #11 — assigned to teammates (Mubarak/Arushi)
- **DISMISSED (4):** #12, #15, #19, #21 — design choices I stand by
- **INVALID (4):** #7 (already fixed), #16 (file already correct), #17 (correct behavior), #18 (file exists)

Real defects in my code: **8** (down from a claimed 21).

When a bug is fixed, the corresponding test should flip from RED to GREEN.
