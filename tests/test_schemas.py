from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.schemas import BookingOutput, Hospital, OutcomeFeedback, TriageOutput


def test_hospital_validates():
    Hospital(
        facility_id="5603", name="INHS Sanjivani", city="Kochi", state="Kerala",
        pincode="682004", facility_type="hospital", lat=9.9312, lon=76.2673,
        trust_score=0.888, trust_calibrated=0.888, trust_source="two-model-verified",
    )


def test_outcome_feedback_validates():
    OutcomeFeedback(
        patient_id="pat_kl_001", facility_id="5603",
        factor="bed", actual_value=1.0,
        ts=datetime.now(timezone.utc),
    )


def test_booking_output_validates():
    BookingOutput(
        transaction_id="abc-123", status="COMMITTED",
        resources={"bed": "OK", "ambulance": "OK", "doctor": "OK", "drug": "OK"},
        facility_id="5603",
    )


def test_triage_validates():
    out = TriageOutput(
        specialty="cardiology",
        urgency=4,
        confidence=0.91,
        required_bed_type="icu",
        fast_path=True,
        red_flag_match=["chest_pain", "diaphoresis"],
        reasoning="Patient presents with acute chest pain and diaphoresis; high suspicion of ACS.",
    )
    assert out.urgency == 4
    assert out.confidence == 0.91
    assert out.required_bed_type == "icu"
    assert out.fast_path is True
    assert "chest_pain" in out.red_flag_match


def test_triage_urgency_below_bound_rejected():
    with pytest.raises(ValidationError):
        TriageOutput(
            specialty="cardiology", urgency=0, confidence=0.5,
            required_bed_type="general", fast_path=False, reasoning="test",
        )


def test_triage_urgency_above_bound_rejected():
    with pytest.raises(ValidationError):
        TriageOutput(
            specialty="cardiology", urgency=6, confidence=0.5,
            required_bed_type="general", fast_path=False, reasoning="test",
        )


def test_triage_invalid_bed_type_rejected():
    with pytest.raises(ValidationError):
        TriageOutput(
            specialty="cardiology", urgency=3, confidence=0.5,
            required_bed_type="ward",  # not in the Literal
            fast_path=False, reasoning="test",
        )


def test_triage_red_flag_match_defaults_to_empty_list():
    out = TriageOutput(
        specialty="neurology", urgency=2, confidence=0.7,
        required_bed_type="hdu", fast_path=False,
        reasoning="Mild neurological symptoms; no red flags triggered.",
    )
    assert out.red_flag_match == []
    # Each instance gets its own list (no shared mutable default)
    out2 = TriageOutput(
        specialty="neurology", urgency=2, confidence=0.7,
        required_bed_type="hdu", fast_path=False,
        reasoning="Second instance.",
    )
    assert out.red_flag_match is not out2.red_flag_match
