import pytest

from app.util import hash_patient_id, round_geo


@pytest.fixture(autouse=True)
def _allow_dev_salt(monkeypatch):
    monkeypatch.setenv("AAROGYANET_DEV", "1")
    monkeypatch.delenv("PII_SALT", raising=False)


def test_hash_patient_id_is_deterministic():
    assert hash_patient_id("aadhaar_123") == hash_patient_id("aadhaar_123")


def test_hash_patient_id_differs_per_input():
    assert hash_patient_id("aadhaar_123") != hash_patient_id("aadhaar_124")


def test_hash_patient_id_format():
    h = hash_patient_id("anything")
    assert h.startswith("p_")
    assert len(h) == 18  # "p_" + 16 hex chars
    int(h[2:], 16)  # raises if non-hex


def test_round_geo_coarsens():
    assert round_geo(9.93128, 76.26731) == (9.93, 76.27)


def test_round_geo_distinct_grid_cells():
    assert round_geo(9.931, 76.267) != round_geo(9.945, 76.281)
