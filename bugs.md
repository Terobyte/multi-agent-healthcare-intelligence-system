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
| 5 | SSE heartbeat doesn't fire every 15s — only triggers when an agent step takes >15s. Render/Cloudflare idle-close after 30-60s | `app/main.py:185` | **MINE** (partial — test is weak) — current impl handles single >15s step (test passes), but does NOT handle "many short agents totalling >15s with no individual step long". Real fix still needs `asyncio.create_task` wall-clock pinger. Test name: `test_sse_heartbeat_must_fire_within_15s_when_agent_step_long` (currently green; rewrite needed to exercise the wall-clock-only path) |
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

---

## 20-Agent Bug Sweep (2026-04-26)

20 parallel `code-reviewer` agents scanned every source file. 19 succeeded, 1
hit rate-limit (`agents/triage.py` — needs re-run). False positives removed.

### CRITICAL — fix before demo

| # | Bug | File:line | Confidence |
|---|-----|-----------|------------|
| 22 | `/book` blocks event loop — sync `book_atomic()` in `def book()` instead of `async def` + `asyncio.to_thread` | `app/main.py:257` | 85 |
| 24 | `StopIteration` crash — `next()` in `_cost_estimate` has no default when `trust_score < 0` | `app/agents/router.py:247` | 100 |
| 26 | API parameter mismatch — `lib/api.ts` passes `query` (string) but `api.ts` expects `{ user_text, language_hint }` — real backend 422s | `arushi/app/src/lib/api.ts:84` | 90 |
| 27 | `conversation_id=""` treated as existing — `is None` should be `not conversation_id` | `app/sponsor/genie.py:109` | 90 |
| 28 | `actual_value` lacks range validation — accepts any float, corrupts `AVG(actual_value)` trust calibration | `app/schemas.py:80` | 100 |
| 29 | Race condition in booking — dup-active-txn SELECT not atomic with parent INSERT (multi-process) | `app/agents/booking.py:92-112` | 95 |
| 30 | Rollback failure leaves orphaned RESERVED resources — parent says ROLLED_BACK but children still RESERVED | `app/agents/booking.py:192-202` | 95 |
| 31 | Idempotency violation — same `txn_id` replay creates duplicate child MERGE rows | `app/agents/booking.py:143` | 90 |
| 32 | SAFE_DEMO doesn't prevent live API calls when pre-baked file is missing | `app/sponsor/voice_narration.py:74` | 95 |
| 33 | EventSource memory leak — StrictMode remount loses old ES ref, old connection stays open | `arushi/app/src/components/ReasoningPanelSSE.tsx:47` | 95 |
| 34 | Empty facility_id passes through to SQL — returns data for wrong facility or full table scan | `app/agents/validator.py:244` | 90 |
| 35 | `warehouse_query` calls in `/outcome` have no try/except — transient DB errors become generic 500 | `app/main.py:489-518` | 90 |

### HIGH — should fix

| # | Bug | File:line | Confidence |
|---|-----|-----------|------------|
| 36 | NGO cache dict accessed without `asyncio.Lock` — concurrent stampede to DB | `app/main.py:571-578` | 80 |
| 37 | `session_id` in SSE endpoints unvalidated — allows log injection, no length/charset check | `app/main.py:291` | 85 |
| 38 | `llm_predicted` lacks range validation — corrupts reputation scoring if outside 0.0-1.0 | `app/schemas.py:81` | 95 |
| 40 | `feedback_id` uses `default=""` instead of `None` — ambiguous falsy state | `app/schemas.py:75` | 85 |
| 41 | `latency_ms` has no bounds — negative or INT_MAX accepted | `app/schemas.py:69` | 85 |
| 42 | Race condition in `WorkspaceClient` init — no lock, multiple inits under concurrency | `app/sponsor/genie.py:71-76` | 85 |
| 43 | `NameError` if SDK response missing `message_id` — `hasattr` check doesn't cover all paths | `app/sponsor/genie.py:114` | 80 |
| 44 | No timeout on Genie `start_conversation_and_wait` — can hang indefinitely | `app/sponsor/genie.py:91-95` | 82 |
| 45 | Genie error log drops message — `type(exc).__name__` without `exc` arg or `exc_info` | `app/sponsor/genie.py:93-95` | 85 |
| 49 | `agent_bricks.py` passes empty symptoms to triage — no early return on blank input | `app/sponsor/agent_bricks.py:70` | 90 |
| 50 | No try/except around `_triage_function()` call — crash propagates to HTTP 500 | `app/sponsor/agent_bricks.py:80` | 85 |
| 51 | Corpus load failure returns `[]` — caller can't distinguish "no matches" from "corpus broken" | `app/sponsor/knowledge_assistant.py:44` | 85 |
| 52 | `int(urgency)` crashes on non-numeric urgency values in corpus | `app/sponsor/knowledge_assistant.py:62` | 80 |
| 53 | Retry button in DoctorCopilot calls `load()` without signal — setState on unmounted | `arushi/app/src/pages/DoctorCopilot.tsx:152` | 100 |
| 54 | Stale closure in useEffect — `selectedReceivingId` dependency overwrites user's selection on data refresh | `arushi/app/src/pages/DoctorCopilot.tsx:91-100` | 85 |
| 55 | `hospital.etaMinutes` renders "undefined min" when field missing | `arushi/app/src/pages/DoctorCopilot.tsx:212` | 90 |
| 56 | SourceModal `onClose` not memoized — re-registers keydown listener every render | `arushi/app/src/components/SourceModal.tsx:43-93` | 90 |
| 57 | Unsafe `Event → MessageEvent<string>` cast — `data` is undefined on real network errors | `arushi/app/src/components/ReasoningPanelSSE.tsx:103-109` | 85 |
| 58 | NaN/Infinity coords crash `L.latLngBounds` in HospitalMap | `arushi/app/src/components/HospitalMap.tsx:48-56` | 82 |
| 59 | Geolocation race — first render uses Mumbai defaults before async position resolves | `arushi/app/src/lib/adapter.ts:31-47` | 80 |
| 60 | Mock `ReserveResponse` missing `status`, `transaction_id` fields — mock vs real divergence | `arushi/app/src/lib/api.ts:182-188` | 95 |
| 61 | `reserve()` type mismatch — spread of `out` may include undefined values | `arushi/app/src/lib/api.ts:170-179` | 85 |
| 62 | NGO data fetch inconsistent error handling — auth errors thrown as exceptions, not degraded flag | `arushi/app/src/lib/api.ts:212-232` | 85 |
| 63 | Symptoms not sanitized in sponsor route handler — defense-in-depth gap | `app/sponsor/routes.py:73` | 95 |
| 64 | `conversation_id` allows arbitrary strings — no format or ownership validation | `app/sponsor/routes.py:96` | 85 |
| 65 | `demo_id` latent path traversal — allowlist protects now but no charset restriction | `app/sponsor/routes.py:114` | 85 |
| 66 | No security logging when sponsor feature flags disabled — no audit trail of probe attempts | `app/sponsor/routes.py:68-69` | 85 |
| 67 | No response size limit on `/sponsor/narrate` streaming — unbounded if sidecar compromised | `app/sponsor/routes.py:106-124` | 85 |
| 68 | `eta_min=0` allowed — misleading "ambulance arrives in 0 minutes" | `app/sponsor/routes.py:41` | 85 |
| 69 | Sidecar response buffered entirely in memory — defeats streaming purpose | `app/sponsor/voice_narration.py:135-136` | 85 |
| 70 | File read in `_read_chunks` has no OSError handling — crashes on corrupt/missing file | `app/sponsor/voice_narration.py:101-108` | 85 |
| 71 | Redundant `resp.aclose()` in CancelledError — double-close risk with httpx context manager | `app/agents/reasoning_stream.py:65` | 85 |
| 72 | Race condition in salt cache — double-checked locking uses `globals()` indirection | `app/util.py:51-72` | 90 |
| 73 | No partial resource availability check before booking saga — all-or-nothing UX | `app/agents/booking.py:131-159` | 85 |
| 74 | No expiration of stale RESERVED transactions — stuck txns block patient forever | `app/agents/booking.py:92-96` | 90 |
| 75 | No transaction isolation for concurrent child MERGEs — same resource can be double-booked | `app/agents/booking.py:146-154` | 85 |
| 76 | No facility resource capacity validation — booking created for facility with no beds | `app/agents/booking.py:78-89` | 85 |
| 77 | `feedback_id` key built from unsanitized user input — control chars in hash | `app/main.py:507-510` | 80 |

### Clean zones (0 bugs)

`app/db.py`, `app/settings.py`, `app/sponsor/scrub.py`, `PatientFlow.tsx`, `NGODashboard.tsx`

### Not reviewed

`app/agents/triage.py` — agent hit rate limit, needs manual re-run

### Negative test coverage added / reconciled

After removing false positives, the 2026-04-26 sweep lists **50 findings**.
Coverage is split between the new pytest file and pre-existing backend/frontend
tests. Current run of `pytest -q tests/test_known_bugs_sweep_2026_04_26.py` is
expected to be red while these bugs remain open.

| Bug | Negative test / status |
|---|---|
| 22 | `tests/test_known_bugs_sweep_2026_04_26.py::test_bug22_book_route_must_not_block_event_loop` |
| 24 | `tests/test_known_bugs_sweep_2026_04_26.py::test_bug24_negative_trust_cost_estimate_must_not_crash` |
| 26 | `tests/test_known_bugs_sweep_2026_04_26.py::test_bug26_frontend_recommend_sends_backend_contract_keys` |
| 27 | `tests/test_known_bugs_sweep_2026_04_26.py::test_bug27_blank_conversation_id_starts_new_genie_conversation` |
| 28 | `tests/test_known_bugs_sweep_2026_04_26.py::test_bug28_38_outcome_scores_must_be_probability_bounded[actual_value-*]` |
| 29 | Existing: `tests/test_known_bugs_saga.py::test_bug6_concurrent_book_atomic_must_not_double_commit` + `tests/test_known_bugs_regression_sweep.py::test_bug6_ten_concurrent_calls_same_patient_only_one_commits` |
| 30 | Existing: `tests/test_neg_booking_rollback_drift.py::test_rollback_failure_must_not_be_reported_as_clean_rolled_back` |
| 31 | Existing: `tests/test_neg_booking_idempotency.py::test_neg_book_atomic_with_same_txn_id_is_not_idempotent` |
| 32 | `tests/test_known_bugs_sweep_2026_04_26.py::test_bug32_safe_demo_missing_voice_file_must_not_call_live_sidecar` |
| 33 | `tests/test_known_bugs_sweep_2026_04_26.py::test_bug33_reasoning_panel_strictmode_cleanup_must_close_previous_eventsource` |
| 34 | `tests/test_known_bugs_sweep_2026_04_26.py::test_bug34_validator_rejects_blank_facility_id_before_query` |
| 35 | `tests/test_known_bugs_sweep_2026_04_26.py::test_bug35_outcome_route_wraps_every_warehouse_call_in_http_errors` |
| 36 | `tests/test_known_bugs_sweep_2026_04_26.py::test_bug36_ngo_cache_access_must_be_guarded_by_asyncio_lock` |
| 37 | `tests/test_known_bugs_sweep_2026_04_26.py::test_bug37_sse_session_id_must_have_length_and_charset_validation` |
| 38 | `tests/test_known_bugs_sweep_2026_04_26.py::test_bug28_38_outcome_scores_must_be_probability_bounded[llm_predicted-*]` |
| 40 | `tests/test_known_bugs_sweep_2026_04_26.py::test_bug40_feedback_id_default_must_be_none_not_empty_string` |
| 41 | `tests/test_known_bugs_sweep_2026_04_26.py::test_bug41_intake_latency_ms_must_have_bounds` |
| 42 | `tests/test_known_bugs_sweep_2026_04_26.py::test_bug42_genie_workspace_init_must_be_locked` |
| 43 | `tests/test_known_bugs_sweep_2026_04_26.py::test_bug43_genie_response_id_resolution_must_use_safe_getattr_default` |
| 44 | `tests/test_known_bugs_sweep_2026_04_26.py::test_bug44_genie_wait_calls_must_have_timeout_kwarg` |
| 45 | `tests/test_known_bugs_sweep_2026_04_26.py::test_bug45_genie_live_error_log_must_include_exception_message` |
| 49 | `tests/test_known_bugs_sweep_2026_04_26.py::test_bug49_blank_agent_bricks_input_must_not_call_triage` |
| 50 | `tests/test_known_bugs_sweep_2026_04_26.py::test_bug50_agent_bricks_triage_errors_return_safe_fallback` |
| 51 | `tests/test_known_bugs_sweep_2026_04_26.py::test_bug51_corpus_load_failure_must_surface_broken_source` |
| 52 | `tests/test_known_bugs_sweep_2026_04_26.py::test_bug52_knowledge_assistant_skips_bad_urgency_rows` |
| 53 | `tests/test_known_bugs_sweep_2026_04_26.py::test_bug53_doctor_retry_must_reuse_abort_signal` |
| 54 | `tests/test_known_bugs_sweep_2026_04_26.py::test_bug54_selected_receiving_effect_must_not_depend_on_current_selection` |
| 55 | `tests/test_known_bugs_sweep_2026_04_26.py::test_bug55_doctor_eta_render_must_guard_missing_eta` |
| 56 | `tests/test_known_bugs_sweep_2026_04_26.py::test_bug56_source_modal_keydown_handler_must_not_depend_on_unmemoized_onclose` |
| 57 | `tests/test_known_bugs_sweep_2026_04_26.py::test_bug57_eventsource_error_handler_must_not_cast_event_to_messageevent` |
| 58 | `tests/test_known_bugs_sweep_2026_04_26.py::test_bug58_hospital_map_filters_non_finite_coordinates` |
| 59 | Existing frontend: `arushi/app/src/__tests__/known_bugs_perf.test.tsx` geolocation test |
| 60 | `tests/test_known_bugs_sweep_2026_04_26.py::test_bug60_mock_reserve_response_must_include_real_backend_fields` |
| 61 | `tests/test_known_bugs_sweep_2026_04_26.py::test_bug61_reserve_must_not_spread_or_forward_undefined_backend_values` |
| 62 | `tests/test_known_bugs_sweep_2026_04_26.py::test_bug62_ngo_data_auth_errors_must_set_degraded_flag_before_throwing` |
| 63 | `tests/test_known_bugs_sweep_2026_04_26.py::test_bug63_sponsor_symptoms_must_be_sanitized_in_route_handler` |
| 64 | `tests/test_known_bugs_sweep_2026_04_26.py::test_bug64_sponsor_conversation_id_must_have_charset_pattern` |
| 65 | `tests/test_known_bugs_sweep_2026_04_26.py::test_bug65_demo_id_must_have_charset_pattern` |
| 66 | `tests/test_known_bugs_sweep_2026_04_26.py::test_bug66_disabled_sponsor_feature_probes_must_be_security_logged` |
| 67 | `tests/test_known_bugs_sweep_2026_04_26.py::test_bug67_sponsor_narrate_stream_must_have_response_size_limit` |
| 68 | `tests/test_known_bugs_sweep_2026_04_26.py::test_bug68_sponsor_narrate_eta_zero_must_be_rejected` |
| 69 | `tests/test_known_bugs_sweep_2026_04_26.py::test_bug69_voice_sidecar_must_stream_not_buffer_entire_response` |
| 70 | `tests/test_known_bugs_sweep_2026_04_26.py::test_bug70_read_chunks_handles_oserror` |
| 71 | `tests/test_known_bugs_sweep_2026_04_26.py::test_bug71_reasoning_stream_cancel_path_must_not_double_close_response` |
| 72 | `tests/test_known_bugs_sweep_2026_04_26.py::test_bug72_salt_cache_must_use_explicit_lock_not_globals_indirection` |
| 73 | `tests/test_known_bugs_sweep_2026_04_26.py::test_bug73_booking_checks_partial_resource_availability_before_saga` |
| 74 | `tests/test_known_bugs_sweep_2026_04_26.py::test_bug74_booking_expires_stale_reserved_transactions` |
| 75 | `tests/test_known_bugs_sweep_2026_04_26.py::test_bug75_child_resource_merge_must_lock_on_facility_resource_not_txn_only` |
| 76 | `tests/test_known_bugs_sweep_2026_04_26.py::test_bug76_booking_validates_facility_has_required_capacity` |
| 77 | `tests/test_known_bugs_sweep_2026_04_26.py::test_bug77_feedback_id_hash_input_must_strip_control_chars` |

---

## Tero Sweep (2026-04-26 evening) — bugs #78–114

37 findings reported by Tero after the live `/book` 500 (icu_beds schema drift,
fixed in commit `16b511c`). Numbered to continue from the prior sweep. Some
overlap with earlier bugs; kept distinct so each gets a dedicated negative test
in `tests/test_bugs_2026_04_26.py`.

### P0 — критические

| # | Bug | File:line |
|---|-----|-----------|
| 78 | Double-booking race — check-then-act без атомарного инкремента; два параллельных запроса проходят capacity check одновременно → overbooking | `app/agents/booking.py:106-131` |
| 79 | SQL-интерполяция `pk_col` в f-string MERGE — whitelist для `table` есть, для `pk_col` нет | `app/agents/booking.py:201-209` |
| 80 | Orphaned RESERVED rows — parent INSERT auto-commit'ится; если коннект падает до child MERGEs, parent остаётся RESERVED навсегда | `app/agents/booking.py:156-194` |
| 81 | `float(row.get("p_bed") or 0.0)` — NULL `p_bed` → 0.0 → composite score обнуляется → больница вылетает из выдачи | `app/agents/router.py:455` |
| 82 | `trust=0.0 treated as missing` — `float(... or ...)` трактует 0.0 как falsy → fallback на `trust_score` вместо `trust_calibrated` | `app/agents/router.py:452` |
| 83 | Markdown fence crash — `raw.split("```", 2)[1]` → `IndexError` если LLM вернёт только один fence | `app/agents/triage.py:296-300` |
| 84 | Format string crash — `f"v1={v1:.2f}"` на `None` → `TypeError` (single-model данные) | `app/agents/validator.py:158` |
| 85 | Chunked transfer bypass — body size middleware проверяет только `Content-Length`; chunked encoding проходит без лимита | `app/main.py:135-148` |
| 86 | Negative `Content-Length` — `int("-100") > 65536 → False`, запрос проходит | `app/main.py:135-148` |
| 87 | Conversation ID auth bypass — любой `conversation_id` принимается без проверки ownership | `app/sponsor/genie.py:122-140` |
| 88 | FD leak — файловый дескриптор не закрывается, если consumer прерывает generator раньше времени | `app/sponsor/voice_narration.py:110-135` |

### P1 — важные

| # | Bug | File:line |
|---|-----|-----------|
| 89 | `_scrubbed_500` без `trace_id` — все 5xx выглядят одинаково, Databricks outage и capacity rejection неразличимы | `app/main.py:269-276` |
| 90 | Naive datetime crash — клиент шлёт `datetime` без timezone, `fb.ts > now` → `TypeError` | `app/main.py:499-503` |
| 91 | Thread pool exhaustion — `_fm_executor(max_workers=2)` зависает навсегда, если Databricks API hang'ает дважды | `app/main.py:207-243` |
| 92 | `X-Forwarded-For` spoofing — rate limit обходится подстановкой произвольного IP в XFF | `app/main.py:159-172` |
| 93 | SSE heartbeat race — heartbeat не проверяет `disconnect`/`producer.done()`, queue растёт без лимита | `app/main.py:321-350` |
| 94 | SSE cleanup — `await t` вместо `asyncio.gather(return_exceptions=True)` — исключение оставит heartbeat незаканселленным | `app/main.py:352-370` |
| 95 | Rollback partial failure — если один child cancellation падает, loop продолжает; одни children RESERVED, другие CANCELLED | `app/agents/booking.py:269-281` |
| 96 | Нет классификации ошибок — timeout и constraint violation обрабатываются одинаково, нет retry для retryable errors | `app/agents/booking.py:214-216` |
| 97 | Cartesian product risk — `LEFT JOIN` без `GROUP BY`/`DISTINCT` на `facility_id` → дубли если `v_trust_calibrated` имеет >1 row | `app/agents/router.py:281-282` |
| 98 | Unknown city silent fallback — неизвестный город молча подставляет центр Индии без warning | `app/agents/router.py:172` |
| 99 | Pydantic `ValidationError` не в `except` списке (только `ValueError`) | `app/agents/triage.py:184` |
| 100 | Unicode control char gap — regex фильтрует только ASCII controls; Unicode C1/bidi/zero-width проходят | `app/agents/triage.py:82` |
| 101 | `WorkspaceClient` init hang — нет timeout при создании клиента → блокирует workers | `app/sponsor/genie.py:77-86` |
| 102 | `httpx.stream(timeout=10.0)` — только read timeout, TCP SYN hang'ает worker (нужен `Timeout(connect=...)`) | `app/sponsor/voice_narration.py:160` |
| 103 | Silent empty string — malformed input → `_extract_user_text()` возвращает `""` → triage падает, ошибка маскируется | `app/sponsor/agent_bricks.py:41-60` |
| 104 | 429 не обрабатывается в `reserve()` — 6-й клик показывает "Reservation failed. Please retry." вместо "Too many bookings" | `arushi/app/src/lib/api.ts:145-159` |
| 105 | Silent mock fallback — `/recommend` падает → пользователь видит фейковые больницы с маленьким баннером | `arushi/app/src/lib/api.ts:104-127` |
| 106 | Нет connection pooling — каждый query = новый коннект → connection exhaustion под нагрузкой | `app/db.py:33-39` |
| 107 | Hardcoded 2s sleep на retry — нет exponential backoff, thundering herd при холодном warehouse | `app/db.py:47` |

### P2 — менее критичные

| # | Bug | File:line |
|---|-----|-----------|
| 108 | False positive — regex `\b[a-f0-9]{32}\b` красит легитимные MD5 / transaction ID как PII | `app/sponsor/scrub.py:24` |
| 109 | Missing httpx timeout handling — ловит только `CancelledError` (не `TimeoutException`/`ReadError`) | `app/agents/reasoning_stream.py:27-67` |
| 110 | Hash collision risk — только 16 hex chars (64 bit) для patient ID hash | `app/util.py:83` |
| 111 | Float precision — `1.0000000000000002` пройдёт `le=1.0` validator | `app/schemas.py:25-26` |
| 112 | Schema mismatch — `RankedHospital` имеет `hospital_id`, property alias `facility_id` может ломать frontend | `contracts/schemas.py` ↔ `app/agents/router.py` |
| 113 | Silent corpus degradation — если >10% rows malformed, возвращается пустой результат без warning | `app/sponsor/knowledge_assistant.py:74-80` |
| 114 | Flag read race — два `os.getenv()` без атомарности между check и parse | `app/sponsor/flags.py:12-16` |

Negative tests for #78–114 live in `tests/test_bugs_2026_04_26.py` (and the
matching frontend file `arushi/app/src/__tests__/bugs_2026_04_26.test.tsx`).
Each test that PASSES today proves the bug is real and reproducible. After a
fix lands, the same test should FAIL with the new behaviour, prompting an
update of the assertion to lock in the fix.

---

## Sweep #2 — top-10 boundary failures (2026-04-26 evening)

A second pass classified findings by the *boundary* being violated rather
than by file. The unifying theme: every critical bug is a missing contract at
a system boundary, not a single typo.

| Boundary       | What it guarantees                          | Critical bug       |
|----------------|---------------------------------------------|--------------------|
| transaction    | distributed lock + atomic CAS               | #1, #2, #3         |
| backpressure   | bounded queue + deadline-based put          | #4                 |
| contract       | None vs zero preserved through pipelines    | #5, #6 (closed)    |
| io_deadline    | wall-clock SLA on every external call       | #7                 |
| tenant         | ownership check before resource access      | #8                 |
| secret         | defense-in-depth scrubber                   | #9                 |
| exception      | exhaustive taxonomy at I/O surface          | #10                |

`app/boundaries.py` provides three helpers (`with_io_deadline`, `bounded_put`,
`as_owner`) so future code can opt into the contract. Negative tests live in
`tests/test_critical_bugs_2026_04_26.py`.

**Closed in this sweep:**

- #3 — `rollback_drift` alert log on ROLLBACK_FAILED (`booking.py`)
- #4 — SSE producer + heartbeat use `bounded_put` (`main.py`)
- #5, #6 — None-vs-zero traps removed in router (`router.py`)
- #7 — `with_io_deadline` wraps `outcome_route` + `ngo_data_endpoint` warehouse calls
- #8 — `GenieClient.ask` records owner on first use, refuses cross-tenant resume
- #9 — `apply_sponsor_patterns` redacts bare 32-hex except in safe contexts (`transaction_id=` etc.)
- #10 — `reasoning_stream` catches `httpx.HTTPError` parent

**Open (architectural — deferred for hackathon scope):**

- #1 — `_patient_lock` is `threading.Lock`. Two Railway replicas can both
  win. Real fix: warehouse-side unique constraint on
  `(patient_id_hash, status='RESERVED')` or Redis SETNX. For the demo the
  service runs a single replica, so this never triggers.
- #2 — dup-active-txn check is a SELECT then a separate INSERT. Two
  concurrent callers on the same patient can both pass the SELECT. Real fix:
  rewrite the parent INSERT as `MERGE INTO txn_atomic ... USING (SELECT ...
  WHERE NOT EXISTS in ('RESERVED','COMMITTED'))` so the gate is one
  statement. Touches 6 saga tests + the booking idempotency suite — left for
  a focused PR.
