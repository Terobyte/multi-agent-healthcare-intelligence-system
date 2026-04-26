"""TDD tests for triage.py bugs A and B.

Bug A: module-level corpus load crashes on import when symptom_corpus.json is missing.
Bug B: red-flag urgency boost does not update bed_type to match the boosted urgency.
"""
import importlib
import sys


def test_triage_imports_when_corpus_missing(monkeypatch, tmp_path):
    """Bug A: removing symptom_corpus.json must not crash module import.

    After fix, _load_corpus returns empty corpus + empty red_flags so that
    _keyword_triage falls back to ('general medicine', 2, 'general') without
    raising FileNotFoundError at import time.
    """
    # Purge any cached import so we get a fresh module load
    sys.modules.pop("app.agents.triage", None)

    # Make VS_ENDPOINT empty so triage() skips the LLM path entirely
    monkeypatch.setenv("VS_ENDPOINT", "")

    # Patch _CORPUS_FILE on the module BEFORE the module-level call executes.
    # We do this by injecting a bad path into the module's globals after import
    # would fail, so instead we reload with a patched Path.open.
    #
    # Strategy: monkeypatch the open call on pathlib.Path so that any attempt
    # to open a file named "symptom_corpus.json" raises FileNotFoundError.
    original_open = None

    def _patched_open(self, *args, **kwargs):
        if self.name == "symptom_corpus.json":
            raise FileNotFoundError(f"Simulated missing corpus: {self}")
        # Fall back to the real open for all other files
        import builtins
        return builtins.open(self, *args, **kwargs)

    import pathlib
    original_open = pathlib.Path.open
    monkeypatch.setattr(pathlib.Path, "open", _patched_open)

    # Import must succeed — Bug A fix: no FileNotFoundError propagated
    triage_mod = importlib.import_module("app.agents.triage")

    result = triage_mod.triage("test")
    assert result.specialty == "general medicine"
    assert result.urgency == 2


def test_red_flag_boost_updates_bed_type():
    """Bug B: when red-flag boosts urgency to 4, bed_type must match (hdu, not general).

    'diaphoresis' is in red_flags but NOT in any corpus keyword list, so
    _keyword_triage will: (a) set best=None → default ('general medicine', 2, 'general'),
    (b) detect the red-flag match and boost urgency to 4, but (before fix) leaves
    bed_type='general' — clinically inconsistent with urgency=4.
    """
    # Use a fresh import to avoid state from test A's monkeypatched run
    sys.modules.pop("app.agents.triage", None)
    import app.agents.triage as triage_mod

    # 'diaphoresis' is in red_flags, not in any corpus keyword → no corpus match,
    # only the red-flag boost fires.
    result = triage_mod._keyword_triage("zzz_no_corpus_match diaphoresis zzz")

    assert "diaphoresis" in result.red_flag_match, result
    # urgency should be boosted to >=4 by the red-flag override
    assert result.urgency >= 4, result
    # Bug-B fix: bed_type must align with urgency, NOT remain "general"
    expected = "icu" if result.urgency >= 5 else "hdu"
    assert result.required_bed_type == expected, result
