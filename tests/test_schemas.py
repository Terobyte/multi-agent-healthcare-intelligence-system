from datetime import datetime, timezone

from app.schemas import BookingOutput, Hospital, OutcomeFeedback


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
