"""Shared Pydantic schemas for Healthcare Multi-Agent Intelligence System.

All 4 owners import from here. If you change a schema, update the matching
mock JSON file in this folder in the same commit.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


# ─────────────────────────── Sub-agent inputs ───────────────────────────


class TriageInput(BaseModel):
    user_text: str
    language_hint: Literal["hi", "en", "auto"] = "auto"
    context: dict = Field(default_factory=dict)


class PredictorInput(BaseModel):
    specialty: str
    city: str
    timestamp: datetime
    candidate_hospital_ids: list[str]


class RouterInput(BaseModel):
    specialty: str
    city: str
    predictions: list["BedPrediction"]


class TransferInput(BaseModel):
    sending_hospital_id: str
    patient_summary: dict
    receiving_hospitals: list["RankedHospital"]
    trace_id: str


class VoiceVerifyInput(BaseModel):
    hospital_id: str
    specialty: str
    question_template: str = "Kya aapke paas {specialty} ke liye bed khali hai?"
    mode: Literal["mock", "realtime", "twilio"] = "mock"


# ─────────────────────────── Sub-agent outputs ───────────────────────────


class TriageOutput(BaseModel):
    specialty: str
    urgency: int = Field(ge=1, le=5)
    symptoms_parsed: list[str]
    confidence: float = Field(ge=0.0, le=1.0)
    trace_id: str


class BedPrediction(BaseModel):
    hospital_id: str
    p_bed: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    last_sample_age_min: int


class PredictorOutput(BaseModel):
    predictions: list[BedPrediction]
    model_version: str
    trace_id: str


class RankedHospital(BaseModel):
    hospital_id: str
    name: str
    travel_min: int
    specialty_match: float = Field(ge=0.0, le=1.0)
    cost_estimate_inr: int
    non_medical_cost_inr: int
    lat: float
    lon: float


class RouterOutput(BaseModel):
    ranked: list[RankedHospital]
    genie_query_id: str
    trace_id: str


class ReceivingHospital(BaseModel):
    hospital_id: str
    name: str
    capability_score: float = Field(ge=0.0, le=1.0)
    travel_min: int
    p_bed: float = Field(ge=0.0, le=1.0)


class TransferOutput(BaseModel):
    receiving_hospitals: list[ReceivingHospital]
    referral_packet_url: str
    fhir_snippet: str
    ambulance_eta_min: int
    d2d_handoff_id: str
    trace_id: str


class VoiceOutput(BaseModel):
    hospital_id: str
    original_p_bed: float = Field(ge=0.0, le=1.0)
    verified_p_bed: float = Field(ge=0.0, le=1.0)
    confidence_after_voice: float = Field(ge=0.0, le=1.0)
    verified_at: datetime
    raw_transcript: str
    audio_url: str | None = None
    mode_used: Literal["mock", "realtime", "twilio"]
    trace_id: str


# ─────────────────────────── Supervisor response ───────────────────────────


class SupervisorResponse(BaseModel):
    """Final payload Databricks App renders. Aggregates outputs from sub-agents."""

    intent: Literal["patient_triage", "doctor_transfer"]
    verifying: bool = False
    triage: TriageOutput | None = None
    hospitals: list[RankedHospital] = Field(default_factory=list)
    voice_verification: VoiceOutput | None = None
    transfer: TransferOutput | None = None
    trace_ids: list[str] = Field(default_factory=list)


# Forward refs
RouterInput.model_rebuild()
TransferInput.model_rebuild()
