"""Negative regression locks for the 2026-04-26 bugs.md sweep.

These tests intentionally encode the *desired* behavior for confirmed sweep
findings. They are expected to fail while the bug is still present, and flip
green when the implementation is fixed.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic import ValidationError


ROOT = Path(__file__).resolve().parent.parent


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def _function_node(rel: str, name: str) -> ast.FunctionDef | ast.AsyncFunctionDef:
    tree = ast.parse(_read(rel), filename=rel)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return node
    raise AssertionError(f"could not find function {name} in {rel}")


def _class_node(rel: str, name: str) -> ast.ClassDef:
    tree = ast.parse(_read(rel), filename=rel)
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == name:
            return node
    raise AssertionError(f"could not find class {name} in {rel}")


def _assigned_field_call(cls: ast.ClassDef, field_name: str) -> ast.Call:
    for node in cls.body:
        if not isinstance(node, ast.AnnAssign):
            continue
        if isinstance(node.target, ast.Name) and node.target.id == field_name:
            if isinstance(node.value, ast.Call):
                return node.value
            raise AssertionError(f"{field_name} exists but is not Field(...)")
    raise AssertionError(f"{field_name} not found on {cls.name}")


def _field_kw_names(field_call: ast.Call) -> set[str]:
    return {kw.arg for kw in field_call.keywords if kw.arg}


def test_bug22_book_route_must_not_block_event_loop() -> None:
    """`/book` must be async and offload sync DB saga via asyncio.to_thread."""
    tree = ast.parse((ROOT / "app" / "main.py").read_text(), filename="app/main.py")
    book_fn = next(
        n for n in tree.body
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == "book"
    )

    assert isinstance(book_fn, ast.AsyncFunctionDef), (
        "bug #22: app.main.book is a sync FastAPI handler. It calls the sync "
        "book_atomic() saga directly, so concurrent requests can occupy the "
        "server worker instead of yielding through asyncio.to_thread()."
    )
    assert any(
        isinstance(n, ast.Call)
        and isinstance(n.func, ast.Attribute)
        and n.func.attr == "to_thread"
        for n in ast.walk(book_fn)
    ), "bug #22: async book() must call asyncio.to_thread(book_atomic, ...)"


def test_bug24_negative_trust_cost_estimate_must_not_crash() -> None:
    """Router cost heuristic must handle malformed negative trust defensively."""
    from app.agents.router import _cost_estimate

    try:
        medical_cost, travel_cost = _cost_estimate(-0.01, 10.0)
    except StopIteration as exc:  # current bug: next(...) has no default
        pytest.fail(f"bug #24: negative trust_score crashes _cost_estimate: {exc!r}")

    assert medical_cost >= 0
    assert travel_cost >= 0


def test_bug26_frontend_recommend_sends_backend_contract_keys() -> None:
    """Canonical api.ts and lib/api.ts call site must both use backend contract."""
    canon = _read("arushi/app/src/api.ts")
    start = canon.find("recommend: (")
    end = canon.find("book: (", start) if start != -1 else -1
    recommend_block = canon[start:end] if start != -1 and end != -1 else ""
    assert recommend_block, "could not locate canonical api.recommend block"

    assert "user_text" in recommend_block and "language" in recommend_block, (
        "bug #26 (canon): api.ts must use {user_text, language}, not "
        "language_hint or a raw query string."
    )
    assert "language_hint" not in recommend_block, (
        "bug #26 (canon): language_hint is not accepted by app.main.RecommendRequest"
    )

    # The actual reported bug is in the *caller*: lib/api.ts:84 currently
    # passes the raw query string to canonicalApi.recommend(...). Fix is
    # incomplete unless the call site also forwards an object with user_text.
    lib = _read("arushi/app/src/lib/api.ts")
    call_match = re.search(r"canonicalApi\.recommend\(([^)]*)\)", lib, re.S)
    assert call_match, "could not locate canonicalApi.recommend(...) call in lib/api.ts"
    call_args = call_match.group(1)
    assert "user_text" in call_args, (
        "bug #26 (caller): lib/api.ts passes raw query string to "
        "canonicalApi.recommend; must pass {user_text, language} object."
    )


def test_bug27_blank_conversation_id_starts_new_genie_conversation(monkeypatch) -> None:
    """`conversation_id=""` is absent input, not an existing conversation."""
    from app.sponsor.genie import GenieClient

    calls = {"start": 0, "create": 0}

    class FakeGenie:
        def start_conversation_and_wait(self, **_kwargs):
            calls["start"] += 1
            return SimpleNamespace(
                conversation_id="new-conv",
                message_id="msg-1",
                attachments=[],
            )

        def create_message_and_wait(self, **_kwargs):
            calls["create"] += 1
            return SimpleNamespace(id="msg-existing", attachments=[])

    client = GenieClient()
    client._space_id = "space-123"
    monkeypatch.setattr(client, "_workspace", lambda: SimpleNamespace(genie=FakeGenie()))

    result = client._live_response("", "show ICU beds")

    assert calls == {"start": 1, "create": 0}, (
        "bug #27: blank conversation_id must be treated like None. "
        f"Got calls={calls}, result={result}"
    )
    assert result["conversation_id"] == "new-conv"


@pytest.mark.parametrize(
    "field,value",
    [
        ("actual_value", -0.1),
        ("actual_value", 1.1),
        ("llm_predicted", -0.01),
        ("llm_predicted", 1.01),
    ],
)
def test_bug28_38_outcome_scores_must_be_probability_bounded(field, value) -> None:
    """Outcome calibration inputs must stay in [0, 1]."""
    from datetime import datetime, timezone

    from app.schemas import OutcomeFeedback

    payload = {
        "patient_id": "p1",
        "facility_id": "5603",
        "factor": "bed",
        "actual_value": 1.0,
        "llm_predicted": 0.5,
        "ts": datetime.now(timezone.utc),
    }
    payload[field] = value

    with pytest.raises(ValidationError):
        OutcomeFeedback(**payload)


def test_bug33_reasoning_panel_strictmode_cleanup_must_close_previous_eventsource() -> None:
    """Creating a new EventSource must close any stale ref first."""
    src = _read("arushi/app/src/components/ReasoningPanelSSE.tsx")
    constructor_idx = src.find("new EventSource")
    assert constructor_idx != -1, "precondition: component should create an EventSource"
    before_constructor = src[:constructor_idx]

    assert re.search(r"esRef\.current\?\.close\(\)", before_constructor), (
        "bug #33: StrictMode can run the effect twice before cleanup, and the "
        "new connection overwrites esRef.current without closing the old one."
    )


def test_bug34_validator_rejects_blank_facility_id_before_query(monkeypatch) -> None:
    """Blank facility ids should never be sent to warehouse SQL."""
    from app.agents import validator

    called = {"query": False}

    def fake_query(*_args, **_kwargs):
        called["query"] = True
        return []

    monkeypatch.setattr(validator, "warehouse_query", fake_query)

    with pytest.raises(ValueError, match="facility_id"):
        validator.validate("")

    assert called["query"] is False, "bug #34: blank facility_id reached warehouse_query"


def test_bug35_outcome_route_wraps_every_warehouse_call_in_http_errors() -> None:
    """Transient outcome DB errors should map to explicit 503/422, not generic 500."""
    outcome_fn = _function_node("app/main.py", "outcome_route")
    src = ast.get_source_segment(_read("app/main.py"), outcome_fn) or ""
    assert "warehouse_query" in src, "precondition: /outcome should call warehouse_query"
    assert "except Exception" in src and "HTTPException(status_code=503" in src, (
        "bug #35: /outcome warehouse_query calls are not wrapped. A transient "
        "DB exception escapes as the global generic 500 instead of a clear "
        "service-unavailable response."
    )


def test_bug36_ngo_cache_access_must_be_guarded_by_asyncio_lock() -> None:
    """Shared NGO cache must be protected from concurrent stampedes."""
    src = _read("app/main.py")
    assert "_ngo_cache" in src, "precondition: app uses module-level NGO cache"
    assert "_ngo_cache_lock" in src and "asyncio.Lock" in src, (
        "bug #36: _ngo_cache_lock missing or not declared as asyncio.Lock"
    )
    # The lock has to actually wrap the cache miss path, not just exist as
    # dead code. Easiest invariant: an `async with _ngo_cache_lock` statement
    # appears inside the ngo_data_endpoint coroutine.
    ngo_fn = _function_node("app/main.py", "ngo_data_endpoint")
    ngo_src = ast.get_source_segment(src, ngo_fn) or ""
    assert re.search(r"async with\s+_ngo_cache_lock", ngo_src), (
        "bug #36: _ngo_cache_lock is defined but never used to guard the "
        "_ngo_cache read/write inside ngo_data_endpoint."
    )


def test_bug37_sse_session_id_must_have_length_and_charset_validation() -> None:
    """SSE session ids are logged/reflected, so they need a constrained type alias."""
    src = _read("app/main.py")
    tree = ast.parse(src, filename="app/main.py")

    # The sse function must exist and its session_id parameter must NOT be bare str.
    sse_fn = None
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "sse":
            sse_fn = node
            break
    assert sse_fn is not None, "precondition: async def sse not found in app/main.py"

    session_id_arg = next(
        (a for a in sse_fn.args.args if a.arg == "session_id"), None
    )
    assert session_id_arg is not None, "precondition: sse() has no session_id parameter"
    annotation = session_id_arg.annotation
    assert annotation is not None, "bug #37: session_id has no type annotation"
    if isinstance(annotation, ast.Name):
        assert annotation.id != "str", (
            "bug #37: /sse accepts raw session_id: str with no max_length or "
            "charset validation, allowing log/control-character injection."
        )

    # At module level there must be a type alias (SessionId or similar) built
    # from Annotated[str, Query(max_length=..., pattern=...)].
    # Can be plain assignment (SessionId = Annotated[...]) or annotated.
    found_alias = False
    for node in tree.body:
        value = None
        if isinstance(node, ast.AnnAssign) and isinstance(node.value, ast.Subscript):
            value = node.value
        elif isinstance(node, ast.Assign) and node.targets:
            # SessionId = Annotated[str, Query(...)]
            if isinstance(node.value, ast.Subscript):
                value = node.value
        if value is None:
            continue
        for child in ast.walk(value):
            if isinstance(child, ast.Call):
                func_name = (
                    child.func.id if isinstance(child.func, ast.Name)
                    else child.func.attr if isinstance(child.func, ast.Attribute)
                    else None
                )
                if func_name == "Query":
                    kw_names = {kw.arg for kw in child.keywords if kw.arg}
                    if "max_length" in kw_names and "pattern" in kw_names:
                        found_alias = True
    assert found_alias, (
        "bug #37: no module-level Annotated[str, Query(max_length=..., pattern=...)] "
        "type alias found for session_id validation."
    )


@pytest.mark.parametrize("latency_ms", [-1, 2_147_483_648])
def test_bug41_intake_latency_ms_must_have_bounds(latency_ms) -> None:
    """Negative or absurd latency values must not enter analytics."""
    from app.schemas import IntakeHandshake

    with pytest.raises(ValidationError):
        IntakeHandshake(
            facility_id="5603",
            query="is oxygen available?",
            response="yes",
            signature="sig",
            latency_ms=latency_ms,
        )


def test_bug40_feedback_id_default_must_be_none_not_empty_string() -> None:
    """Empty-string feedback_id makes caller-supplied vs generated state ambiguous."""
    cls = _class_node("app/schemas.py", "OutcomeFeedback")
    field = _assigned_field_call(cls, "feedback_id")
    defaults = [
        kw.value.value for kw in field.keywords
        if kw.arg == "default" and isinstance(kw.value, ast.Constant)
    ]
    assert defaults == [None], (
        f"bug #40: feedback_id should default to None, not {defaults!r}; "
        "empty string is an ambiguous falsy sentinel."
    )


def test_bug42_genie_workspace_init_must_be_locked() -> None:
    """Lazy WorkspaceClient construction must be concurrency-safe."""
    src = _read("app/sponsor/genie.py")
    workspace_fn = _function_node("app/sponsor/genie.py", "_workspace")
    workspace_src = ast.get_source_segment(src, workspace_fn) or ""
    # Module must define an actual Lock instance, not just import the symbol.
    assert re.search(r"Lock\s*\(\s*\)", src), (
        "bug #42: genie module declares no Lock() instance"
    )
    # The lazy-init body must run inside `with <lock>:` to be safe.
    assert re.search(r"with\s+\w*[Ll]ock\w*\s*:", workspace_src), (
        "bug #42: GenieClient._workspace lazy-inits WorkspaceClient without "
        "wrapping the init in a lock; concurrent live requests can create "
        "multiple clients."
    )


def test_bug43_genie_response_id_resolution_must_use_safe_getattr_default() -> None:
    """SDK response id/message_id fallback must use getattr with a safe default."""
    fn = _function_node("app/sponsor/genie.py", "_live_response")
    # Collect all getattr calls inside _live_response.
    getattr_calls: list[ast.Call] = [
        node for node in ast.walk(fn)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "getattr"
    ]
    assert getattr_calls, "precondition: _live_response must contain getattr calls"

    # Build a set of attribute names that are accessed via getattr(obj, name, default)
    # with exactly 3 positional args (obj, attr_name_string, default_value).
    safe_attrs: set[str] = set()
    for call in getattr_calls:
        if (
            len(call.args) == 3
            and isinstance(call.args[1], ast.Constant)
            and isinstance(call.args[1].value, str)
        ):
            safe_attrs.add(call.args[1].value)

    assert "message_id" in safe_attrs and "id" in safe_attrs, (
        "bug #43: _live_response must use getattr(res, 'message_id', <default>) "
        "and getattr(res, 'id', <default>) with 3-arg form (safe default) for "
        "both attribute names. Got safe attrs: " + repr(safe_attrs)
    )


def test_bug44_genie_wait_calls_must_have_timeout_kwarg() -> None:
    """Genie wait APIs can hang indefinitely without explicit timeout."""
    src = _read("app/sponsor/genie.py")
    for call_name in ("start_conversation_and_wait", "create_message_and_wait"):
        m = re.search(rf"{call_name}\((.*?)\)", src, re.S)
        assert m, f"precondition: {call_name} call not found"
        assert "timeout" in m.group(1), (
            f"bug #44: {call_name} has no timeout kwarg, so live Genie can hang indefinitely."
        )


def test_bug45_genie_live_error_log_must_include_exception_message() -> None:
    """Fallback logs should include exception type AND message text."""
    fn = _function_node("app/sponsor/genie.py", "ask")
    src = _read("app/sponsor/genie.py")
    fn_src = ast.get_source_segment(src, fn) or ""

    # Find the ExceptHandler inside ask().
    has_type_name = False
    has_exc_ref = False
    for node in ast.walk(fn):
        if not isinstance(node, ast.ExceptHandler):
            continue
        # Walk the handler body looking for a logging call whose args contain
        # both type(exc).__name__ and a reference to exc (bare or str(exc)).
        for child in ast.walk(node):
            if not isinstance(child, ast.Call):
                continue
            # Check all positional args and keyword values of the call.
            all_args = list(child.args) + [kw.value for kw in child.keywords]
            type_found = any(
                isinstance(a, ast.Attribute)
                and isinstance(a.value, ast.Call)
                and isinstance(a.value.func, ast.Name)
                and a.value.func.id == "type"
                and a.attr == "__name__"
                for a in all_args
            )
            exc_found = any(
                (isinstance(a, ast.Name) and a.id == "exc")
                or (
                    isinstance(a, ast.Call)
                    and isinstance(a.func, ast.Name)
                    and a.func.id == "str"
                    and a.args
                    and isinstance(a.args[0], ast.Name)
                    and a.args[0].id == "exc"
                )
                for a in all_args
            )
            if type_found:
                has_type_name = True
            if exc_found:
                has_exc_ref = True

    assert has_type_name and has_exc_ref, (
        "bug #45: genie live error log must include BOTH type(exc).__name__ "
        "AND exc (or str(exc)) in the logging call args so the log captures "
        "the exception type AND the message. "
        f"found type_name={has_type_name}, exc_ref={has_exc_ref}"
    )


def test_bug32_safe_demo_missing_voice_file_must_not_call_live_sidecar(monkeypatch) -> None:
    """SAFE_DEMO is a hard kill-switch for live voice API calls."""
    from app.sponsor import voice_narration

    monkeypatch.setenv("SAFE_DEMO", "1")
    monkeypatch.setenv("SPONSOR_VOICE", "1")
    monkeypatch.setattr(voice_narration, "_try_file", lambda *_args: None)

    called = {"sidecar": False}

    def fake_sidecar(*_args):
        called["sidecar"] = True
        return iter([b"live-audio"])

    monkeypatch.setattr(voice_narration, "_try_sidecar", fake_sidecar)

    with pytest.raises(voice_narration.VoiceUnavailable):
        voice_narration.narrate(demo_id="missing", lang="hi")

    assert called["sidecar"] is False, (
        "bug #32: SAFE_DEMO=1 must never fall through to the live sidecar, "
        "even when the pre-baked file is missing."
    )


def test_bug49_blank_agent_bricks_input_must_not_call_triage(monkeypatch) -> None:
    """Blank sponsor triage input should be rejected before invoking triage()."""
    from app.sponsor import agent_bricks

    def should_not_run(*_args):
        raise RuntimeError("triage should not be called for blank symptoms")

    monkeypatch.setattr(agent_bricks, "_triage_function", should_not_run)

    with pytest.raises(ValueError, match="blank|empty|required"):
        agent_bricks.run_triage("   ", "en")


def test_bug50_agent_bricks_triage_errors_return_safe_fallback(monkeypatch) -> None:
    """Sponsor Agent Bricks wrapper should not propagate raw triage exceptions."""
    from app.sponsor import agent_bricks
    from app.schemas import TriageOutput

    def boom(*_args):
        raise RuntimeError("llm outage")

    monkeypatch.setattr(agent_bricks, "_triage_function", boom)

    result = agent_bricks.run_triage("chest pain", "en")

    assert isinstance(result, TriageOutput), (
        "bug #50: _triage_function exceptions should be caught and converted "
        "to a safe TriageOutput fallback, not propagated to HTTP 500."
    )


def test_bug51_corpus_load_failure_must_surface_broken_source(monkeypatch, tmp_path) -> None:
    """Corpus unavailable is not the same as a valid no-match result."""
    from app.sponsor import knowledge_assistant

    missing = tmp_path / "missing.json"
    monkeypatch.setattr(knowledge_assistant, "_CORPUS_PATH", missing)

    with pytest.raises(RuntimeError, match="corpus"):
        knowledge_assistant._load_corpus()


def test_bug52_knowledge_assistant_skips_bad_urgency_rows() -> None:
    """A single malformed corpus urgency value must not crash retrieval."""
    from app.sponsor.knowledge_assistant import _keyword_match

    corpus = [
        {"keywords": ["fever"], "specialty": "general medicine", "urgency": "red"},
        {"keywords": ["fever"], "specialty": "infectious disease", "urgency": 3},
    ]

    matches = _keyword_match("fever", corpus, k=5)

    assert matches, "valid matching rows should still be returned"
    assert all(isinstance(m["urgency"], int) for m in matches), (
        f"bug #52: malformed urgency rows should be skipped/coerced safely; got {matches}"
    )


def test_bug53_doctor_retry_must_reuse_abort_signal() -> None:
    """Retry click should not start an untracked load after unmount."""
    src = _read("arushi/app/src/pages/DoctorCopilot.tsx")
    assert "onClick={() => void load()}" not in src, (
        "bug #53: retry button calls load() without an AbortSignal, so a "
        "late response can set state after unmount."
    )


def test_bug54_selected_receiving_effect_must_not_depend_on_current_selection() -> None:
    """Data refresh should not overwrite an intentional user selection."""
    src = _read("arushi/app/src/pages/DoctorCopilot.tsx")
    assert "}, [data, selectedReceivingId]);" not in src, (
        "bug #54: selectedReceivingId in the effect dependency list causes "
        "refreshes to reset user choice from a stale closure."
    )


def test_bug55_doctor_eta_render_must_guard_missing_eta() -> None:
    """UI must not render 'undefined min' when ETA is absent."""
    src = _read("arushi/app/src/pages/DoctorCopilot.tsx")
    assert "{hospital.etaMinutes} min" not in src, (
        "bug #55: DoctorCopilot renders hospital.etaMinutes directly, so "
        "missing data appears as 'undefined min'."
    )


def test_bug56_source_modal_keydown_handler_must_not_depend_on_unmemoized_onclose() -> None:
    """Modal keydown listener must not re-register on every parent render.

    If the parent passes an inline onClose, a useEffect whose dependency array
    includes onClose (directly or transitively via useCallback) will detach and
    re-attach the keydown listener on every render. The fix is to store onClose
    in a useRef so the effect closure always reads the latest callback without
    depending on the prop identity.
    """
    src = _read("arushi/app/src/components/SourceModal.tsx")

    # Find the useEffect that registers the keydown listener.
    effect_match = re.search(
        r"useEffect\s*\(\s*\(\)\s*=>\s*\{[^}]*addEventListener\s*\(\s*[\"']keydown[\"']",
        src,
        re.S,
    )
    assert effect_match, "precondition: keydown useEffect not found in SourceModal"

    # Locate the dependency array of that effect — the closing bracket after the
    # effect body, matching the pattern `}, [<deps>]);`.
    effect_start = effect_match.start()
    dep_array_match = re.search(
        r"\}\s*,\s*\[([^\]]*)\]\s*\)\s*;",
        src[effect_start:],
    )
    assert dep_array_match, "precondition: could not locate effect dependency array"
    deps = dep_array_match.group(1)

    # The dependency array must NOT list onClose directly. A ref-stable wrapper
    # (e.g. onCloseRef.current read inside the effect) is the correct pattern.
    assert "onClose" not in deps, (
        "bug #56: keydown useEffect depends on onClose (or a useCallback that "
        "depends on onClose). If the parent passes an inline callback, this "
        "tears down and re-registers the listener every render. Use a ref to "
        "stabilize the callback inside the effect."
    )


def test_bug57_eventsource_error_handler_must_not_cast_event_to_messageevent() -> None:
    """Network EventSource errors are plain Event objects with no data."""
    src = _read("arushi/app/src/components/ReasoningPanelSSE.tsx")
    assert "as MessageEvent<string>" not in src, (
        "bug #57: EventSource.onerror casts Event to MessageEvent<string>, "
        "but real network errors have no .data payload."
    )


def test_bug58_hospital_map_filters_non_finite_coordinates() -> None:
    """Leaflet latLngBounds must only receive finite lat/lng pairs.

    NaN or Infinity from upstream feeds crash L.latLngBounds. The array passed
    to latLngBounds must include a Number.isFinite guard before the call.
    """
    src = _read("arushi/app/src/components/HospitalMap.tsx")

    # Find the latLngBounds call.
    bounds_match = re.search(r"L\.latLngBounds\s*\(", src)
    assert bounds_match, "precondition: L.latLngBounds call not found"

    # Verify that in the window around the latLngBounds call, coordinates are
    # filtered with isFinite before being passed in.
    window_start = max(0, bounds_match.start() - 300)
    window = src[window_start:bounds_match.end() + 200]

    assert re.search(r"isFinite", window), (
        "bug #58: L.latLngBounds receives unfiltered coordinates. NaN or "
        "Infinity from upstream data will crash Leaflet. Filter with "
        "Number.isFinite(lat) && Number.isFinite(lng) before passing to "
        "latLngBounds."
    )


def test_bug60_mock_reserve_response_must_include_real_backend_fields() -> None:
    """Mock reserve() response should match ReserveResponse contract."""
    src = _read("arushi/app/src/lib/api.ts")
    mock_return = re.search(r"await delay\(650\);\s*return\s*{(.*?)};\s*}", src, re.S)
    assert mock_return, "could not locate mock reserve return block"
    block = mock_return.group(1)
    assert "status:" in block and "transaction_id:" in block, (
        "bug #60: mock ReserveResponse omits status and transaction_id, "
        "so dev/offline behavior diverges from the real backend."
    )


def test_bug61_reserve_must_not_spread_or_forward_undefined_backend_values() -> None:
    """reserve() must normalize optional backend fields before returning."""
    src = _read("arushi/app/src/lib/api.ts")
    reserve_block = re.search(r"export async function reserve.*?export async function streamReasoning", src, re.S)
    assert reserve_block, "could not locate reserve() block"
    block = reserve_block.group(0)
    # transaction_id must be null-coalesced (?? null) so undefined never leaks.
    assert re.search(r"transaction_id\s*:\s*\S+\s*\?\?\s*null", block), (
        "bug #61: reserve() can return transaction_id: undefined instead of "
        "normalizing to null via nullish coalescing (?? null)."
    )


def test_bug62_ngo_data_auth_errors_must_set_degraded_flag_before_throwing() -> None:
    """Auth failures in NGO data should update the same degraded signal as other calls."""
    src = _read("arushi/app/src/lib/api.ts")
    ngo_block = re.search(r"export async function getNGODashboardData.*", src, re.S)
    assert ngo_block, "could not locate getNGODashboardData"
    block = ngo_block.group(0)
    auth_branch = re.search(r"err instanceof ApiError.*?status === 403.*?{(.*?)}", block, re.S)
    assert auth_branch and "_degraded = true" in auth_branch.group(1), (
        "bug #62: NGO auth errors set _authError but not _degraded, so "
        "global degraded UI state becomes inconsistent."
    )


def test_bug63_sponsor_symptoms_must_be_sanitized_in_route_handler() -> None:
    """Sponsor route needs defense-in-depth sanitization before agent call."""
    fn = _function_node("app/sponsor/routes.py", "sponsor_triage")
    fn_src = ast.get_source_segment(_read("app/sponsor/routes.py"), fn) or ""

    # There must be a call to sanitize(...) inside sponsor_triage.
    tree = ast.parse(fn_src)
    sanitize_calls = [
        n for n in ast.walk(tree)
        if isinstance(n, ast.Call)
        and isinstance(n.func, ast.Name)
        and n.func.id == "sanitize"
    ]
    assert sanitize_calls, (
        "bug #63: /sponsor/triage passes body.symptoms directly to run_triage "
        "without route-level sanitization."
    )

    # The sanitized result must be forwarded to run_triage (not discarded).
    assert "run_triage" in fn_src, "precondition: sponsor_triage should call run_triage"
    sanitized_var = None
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and isinstance(node.value, ast.Call)
            and isinstance(node.value.func, ast.Name)
            and node.value.func.id == "sanitize"
        ):
            sanitized_var = node.targets[0].id
    assert sanitized_var is not None and sanitized_var in fn_src.partition("run_triage")[2], (
        "bug #63: sanitize() is called but its result is not forwarded to run_triage."
    )


def test_bug64_sponsor_conversation_id_must_have_charset_pattern() -> None:
    """Sponsor Genie conversation ids need format constraints."""
    cls = _class_node("app/sponsor/routes.py", "_SponsorGenieRequest")
    field = _assigned_field_call(cls, "conversation_id")
    assert "pattern" in _field_kw_names(field), (
        "bug #64: conversation_id accepts arbitrary strings; add a charset pattern."
    )


def test_bug65_demo_id_must_have_charset_pattern() -> None:
    """demo_id should be constrained even if allowlist currently protects lookup."""
    cls = _class_node("app/sponsor/routes.py", "_SponsorNarrateRequest")
    field = _assigned_field_call(cls, "demo_id")
    assert "pattern" in _field_kw_names(field), (
        "bug #65: demo_id has max_length but no charset restriction."
    )


def test_bug66_disabled_sponsor_feature_probes_must_be_security_logged() -> None:
    """Disabled sponsor route probes should leave an audit trail per handler."""
    src = _read("app/sponsor/routes.py")
    tree = ast.parse(src, filename="app/sponsor/routes.py")

    # Find every function that raises HTTPException(status_code=404, detail="sponsor_...")
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        has_sponsor_404 = False
        has_logger_warning = False
        for child in ast.walk(node):
            # Check for HTTPException(status_code=404, detail="sponsor_...")
            if isinstance(child, ast.Call):
                func = child.func
                is_http_exc = (
                    (isinstance(func, ast.Name) and func.id == "HTTPException")
                    or (isinstance(func, ast.Attribute) and func.attr == "HTTPException")
                )
                if is_http_exc:
                    status_kw = next((kw for kw in child.keywords if kw.arg == "status_code"), None)
                    detail_kw = next((kw for kw in child.keywords if kw.arg == "detail"), None)
                    if (
                        status_kw
                        and isinstance(status_kw.value, ast.Constant)
                        and status_kw.value.value == 404
                        and detail_kw
                        and isinstance(detail_kw.value, ast.Constant)
                        and isinstance(detail_kw.value.value, str)
                        and detail_kw.value.value.startswith("sponsor_")
                    ):
                        has_sponsor_404 = True
            # Check for logger.warning(...)
            if isinstance(child, ast.Call):
                func = child.func
                if (
                    isinstance(func, ast.Attribute)
                    and func.attr == "warning"
                    and isinstance(func.value, ast.Name)
                    and func.value.id == "logger"
                ):
                    has_logger_warning = True
        if has_sponsor_404:
            assert has_logger_warning, (
                f"bug #66: handler '{node.name}' raises 404 for a disabled sponsor "
                "feature but has no logger.warning audit trail."
            )


def test_bug67_sponsor_narrate_stream_must_have_response_size_limit() -> None:
    """Streaming narration must cap bytes if the sidecar misbehaves."""
    src = _read("app/sponsor/routes.py") + "\n" + _read("app/sponsor/voice_narration.py")
    # A defined integer cap, in bytes.
    cap_decl = re.search(
        r"(?:MAX|LIMIT)_(?:RESPONSE|NARRATE|STREAM|VOICE|AUDIO)_(?:BYTES|SIZE)\s*[:=]\s*\d",
        src,
    )
    assert cap_decl, (
        "bug #67: voice narration must declare a MAX_*_BYTES (or similar) "
        "integer constant capping streamed response size."
    )
    # An abort path that compares running byte count against the cap and
    # stops streaming when exceeded.
    assert re.search(
        r"(>=|>)\s*(?:MAX|LIMIT)_\w*(?:BYTES|SIZE)|exceeded|too[_ -]large",
        src,
        re.I,
    ), (
        "bug #67: cap is declared but no abort/break path enforces it during streaming."
    )


def test_bug68_sponsor_narrate_eta_zero_must_be_rejected() -> None:
    """0-minute ambulance ETA is misleading and must fail validation."""
    from app.sponsor.routes import _SponsorNarrateRequest

    with pytest.raises(ValidationError):
        _SponsorNarrateRequest(demo_id="5603", lang="hi", eta_min=0)


def test_bug69_voice_sidecar_must_stream_not_buffer_entire_response() -> None:
    """Live voice path should iterate response bytes instead of returning resp.content."""
    src = _read("app/sponsor/voice_narration.py")
    assert "resp.content" not in src, (
        "bug #69: _try_sidecar buffers the full audio body in memory via "
        "resp.content, defeating streaming."
    )
    assert "iter_bytes" in src or "stream(" in src, "voice sidecar should stream chunks"


def test_bug70_read_chunks_handles_oserror(monkeypatch, tmp_path) -> None:
    """File read failures should map to VoiceUnavailable/empty fallback, not raw OSError."""
    from app.sponsor.voice_narration import _read_chunks

    missing = tmp_path / "missing.mp3"
    try:
        list(_read_chunks(missing))
    except OSError as exc:
        pytest.fail(f"bug #70: _read_chunks leaks OSError from file IO: {exc!r}")


def test_bug71_reasoning_stream_cancel_path_must_not_double_close_response() -> None:
    """httpx 'async with' already closes responses on cancellation; the
    `except CancelledError:` branch must not call resp.aclose() manually."""
    src = _read("app/agents/reasoning_stream.py")
    # Scope the ban to the CancelledError handler only — legitimate aclose()
    # calls outside an async-with context elsewhere should not be banned.
    cancel_match = re.search(
        r"except\s+asyncio\.CancelledError:.*?(?=\n {0,8}(?:except\b|finally\b|else\b|return\b)|\Z)",
        src,
        re.S,
    )
    assert cancel_match, "precondition: CancelledError handler not found"
    cancel_block = cancel_match.group(0)
    assert ".aclose()" not in cancel_block, (
        "bug #71: CancelledError path manually calls resp.aclose() inside an "
        "httpx 'async with' context manager — risks double-close."
    )


def test_bug72_salt_cache_must_use_explicit_lock_not_globals_indirection() -> None:
    """Salt cache should be boring and lock-protected."""
    src = _read("app/util.py")
    assert "globals()" not in src, (
        "bug #72: hash_patient_id salt cache uses globals() indirection, "
        "which is fragile under concurrent reload/calls."
    )
    assert re.search(r"Lock\s*\(\s*\)", src), (
        "bug #72: salt cache should declare an explicit threading/asyncio Lock()"
    )
    # The salt mutator must hold the lock when assigning the cache.
    salt_fn = _function_node("app/util.py", "_get_salt")
    salt_src = ast.get_source_segment(src, salt_fn) or ""
    assert re.search(r"with\s+_?\w*[Ll]ock\w*\s*:", salt_src), (
        "bug #72: _get_salt must wrap salt cache mutation in 'with <lock>:'"
    )


def test_bug73_booking_checks_partial_resource_availability_before_saga() -> None:
    """Booking should reject unavailable resources before writing parent txn."""
    fn = _function_node("app/agents/booking.py", "_book_atomic_inner")
    fn_src = ast.get_source_segment(_read("app/agents/booking.py"), fn) or ""

    # The parent INSERT must exist inside _book_atomic_inner.
    insert_pos = fn_src.find("INSERT INTO")
    assert insert_pos != -1, "precondition: parent INSERT not found in _book_atomic_inner"
    before_insert = fn_src[:insert_pos]

    # Between function start and the INSERT, there must be a warehouse_query
    # call that checks bed/resource availability (queries bed_reservations or
    # bed_capacity/reserved_beds). This is the partial availability guard.
    assert "bed_reservations" in before_insert or "reserved_beds" in before_insert or "bed_capacity" in before_insert, (
        "bug #73: book_atomic starts the saga (INSERT INTO txn_atomic) without "
        "checking partial resource (bed) availability first."
    )


def test_bug74_booking_expires_stale_reserved_transactions() -> None:
    """Stale RESERVED transactions should not block a patient forever."""
    src = _read("app/agents/booking.py")
    active_select = re.search(r"SELECT transaction_id.*?status IN \('RESERVED','COMMITTED'\).*?LIMIT 1", src, re.S)
    assert active_select, "precondition: active transaction SELECT not found"
    assert "updated_ts" in active_select.group(0) or "created_ts" in active_select.group(0), (
        "bug #74: duplicate-active-txn check ignores transaction age, so "
        "stale RESERVED rows block new bookings forever."
    )


def test_bug75_child_resource_merge_must_lock_on_facility_resource_not_txn_only() -> None:
    """Child reservations must be isolated by concrete resource, not txn id alone."""
    src = _read("app/agents/booking.py")
    # Find every MERGE INTO ... ON ... block in the booking module and confirm
    # at least one of them constrains by facility identity / resource id, not
    # just transaction_id (which never collides between concurrent txns and
    # therefore never blocks the double-book).
    merges = re.findall(r"MERGE INTO[^;]*?ON\s+(.*?)WHEN", src, re.S | re.I)
    assert merges, "precondition: no child MERGE found"
    txn_only = [m for m in merges if re.search(r"transaction_id", m) and not re.search(r"facility_id|resource_id|capacity|pk_col", m, re.I)]
    assert not txn_only, (
        "bug #75: child MERGE ON clause keys only on transaction_id, so "
        "concurrent transactions never collide and the same facility "
        "resource (bed, ambulance, doctor, drug) can be double-booked. "
        "ON must include facility_id and the resource pk so concurrent "
        "writes serialize on capacity, not txn identity."
    )


def test_bug76_booking_validates_facility_has_required_capacity() -> None:
    """A facility row existing is not enough; it needs requested resource capacity."""
    src = _read("app/agents/booking.py")
    facility_lookup = re.search(r"SELECT facility_id FROM workspace\.default\.gold_trust_final.*?\[facility_id\]", src, re.S)
    assert facility_lookup, "precondition: facility existence lookup not found"
    assert "capacity" in facility_lookup.group(0).lower() or "icu_beds" in facility_lookup.group(0).lower(), (
        "bug #76: facility validation only checks existence, not whether the "
        "facility has beds/ambulance/doctor/drug capacity."
    )


def test_bug77_feedback_id_hash_input_must_strip_control_chars() -> None:
    """Generated feedback_id must not hash unsanitized control-character input."""
    fn = _function_node("app/main.py", "outcome_route")
    fn_src = ast.get_source_segment(_read("app/main.py"), fn) or ""

    # Find the key/raw_key assignment line and the hashlib.sha256 call.
    # Between them, re.sub or .translate must appear.
    # NOTE: the hash key may use a pre-hashed patient id (see bug #116) so the
    # patient_id substring isn't required on the f-string line itself — match
    # any raw_key/key f-string assignment.
    lines = fn_src.splitlines()
    key_line_idx = None
    hash_line_idx = None
    for i, line in enumerate(lines):
        if re.search(r"(raw_key|key)\s*=\s*f\"", line):
            if key_line_idx is None:
                key_line_idx = i
        if "sha256" in line and "hashlib" in line:
            if hash_line_idx is None:
                hash_line_idx = i

    assert key_line_idx is not None, "precondition: feedback_id key generation not found"
    assert hash_line_idx is not None, "precondition: hashlib.sha256 hash call not found"
    assert key_line_idx < hash_line_idx, "precondition: key must be generated before hashing"

    between = "\n".join(lines[key_line_idx + 1 : hash_line_idx])
    assert "re.sub" in between or ".translate" in between, (
        "bug #77: feedback_id hash key is built directly from patient/facility "
        "strings with no control-character sanitization between key generation "
        "and hashing."
    )


def test_mubarak_outcome_persists_hashed_patient_id() -> None:
    """outcome_route must hash fb.patient_id before it reaches warehouse_query.

    The booking flow already hashes via hash_patient_id, but /outcome writes
    fb.patient_id directly into the MERGE payload without hashing. The fix
    must introduce a hashed_pid = hash_patient_id(fb.patient_id) line and
    use hashed_pid (not fb.patient_id) in all warehouse_query calls.
    """
    fn = _function_node("app/main.py", "outcome_route")
    src = _read("app/main.py")
    fn_src = ast.get_source_segment(src, fn) or ""

    # 1. hash_patient_id must be called on fb.patient_id somewhere in the function.
    assert re.search(r"hash_patient_id\s*\(\s*fb\.patient_id\s*\)", fn_src), (
        "mubarak #2: outcome_route does not call hash_patient_id(fb.patient_id). "
        "Raw patient_id is written directly into the warehouse MERGE."
    )

    # 2. There must be a local variable (e.g. hashed_pid) receiving the hashed result.
    assert re.search(r"hashed_pid\s*=\s*hash_patient_id\s*\(\s*fb\.patient_id\s*\)", fn_src), (
        "mubarak #2: hash_patient_id(fb.patient_id) is called but its result is "
        "not stored in a local variable like hashed_pid for downstream use."
    )

    # 3. The MERGE warehouse_query params must use hashed_pid, NOT fb.patient_id.
    #    The SQL template uses ? placeholders, so check the Python params list.
    merge_idx = fn_src.find("MERGE INTO")
    assert merge_idx != -1, "precondition: MERGE INTO statement not found in outcome_route"
    after_merge = fn_src[merge_idx:]
    # Find the Python list [...] that supplies the ? params.
    params_match = re.search(r"\[\s*fid,\s*fb\.transaction_id,\s*(\w+)", after_merge)
    assert params_match and params_match.group(1) == "hashed_pid", (
        "mubarak #2: MERGE warehouse_query still uses fb.patient_id instead of "
        "hashed_pid. Raw patient_id leaks into the warehouse."
    )


def test_mubarak_booking_status_allows_rollback_failed() -> None:
    """BookingOutput.status Literal must include ROLLBACK_FAILED if booking.py can produce it.

    booking.py line 258 sets final_status = "ROLLBACK_FAILED" when the parent
    rollback UPDATE itself fails. If BookingOutput.status only allows
    ["COMMITTED", "ROLLED_BACK", "REJECTED"], Pydantic will reject the value
    and the error masks the rollback failure.
    """
    # 1. Confirm booking.py can produce ROLLBACK_FAILED.
    booking_src = _read("app/agents/booking.py")
    assert "ROLLBACK_FAILED" in booking_src, (
        "precondition: booking.py must produce ROLLBACK_FAILED status"
    )

    # 2. Parse BookingOutput.status Literal values from schemas.py.
    tree = ast.parse(_read("app/schemas.py"), filename="app/schemas.py")
    status_literal_values: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef) or node.name != "BookingOutput":
            continue
        for member in node.body:
            if not isinstance(member, ast.AnnAssign):
                continue
            if not isinstance(member.target, ast.Name) or member.target.id != "status":
                continue
            ann = member.annotation
            if (
                isinstance(ann, ast.Subscript)
                and isinstance(ann.value, ast.Name)
                and ann.value.id == "Literal"
            ):
                elts = ann.slice.elts if isinstance(ann.slice, ast.Tuple) else [ann.slice]
                for elt in elts:
                    if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                        status_literal_values.add(elt.value)
            break
        break

    assert status_literal_values, "precondition: could not extract Literal values for BookingOutput.status"

    assert "ROLLBACK_FAILED" in status_literal_values, (
        f"mubarak #3: booking.py can return status='ROLLBACK_FAILED' but "
        f"BookingOutput.status only allows {sorted(status_literal_values)}. "
        "Add 'ROLLBACK_FAILED' to the Literal so Pydantic does not reject "
        "the booking result and mask the rollback failure."
    )
