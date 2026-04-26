from datetime import datetime, timezone

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
