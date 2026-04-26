from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


class Hospital(BaseModel):
    facility_id: str
    name: str
    city: str
    state: str
    pincode: str
    facility_type: str
    lat: float
    lon: float
    trust_score: float            # gold_trust_final.trust_score
    trust_calibrated: float       # v_trust_calibrated.trust_calibrated
    trust_source: Literal["two-model-verified", "models-disagree", "llm-verified", "rule-inferred"]
    max_factor_disagreement: Optional[float] = None


class FactorWithReasoning(BaseModel):
    value: float
    reasoning: str
    source: str


class TrustScorerOutput(BaseModel):
    facility_id: str
    factors: dict[str, FactorWithReasoning]
    trust: float
    trust_calibrated: float
    extractor_reasoning: str
    validator_reasoning: str
    agreement: bool


class BookingOutput(BaseModel):
    transaction_id: Optional[str]            # None if REJECTED before insert
    status: Literal["COMMITTED", "ROLLED_BACK", "REJECTED"]
    resources: dict[str, str]
    facility_id: str
    reason: Optional[str] = None             # human-readable reason for REJECTED/ROLLED_BACK
    commit_error: Optional[str] = None       # set when children OK but parent COMMIT update raised


class IntakeHandshake(BaseModel):
    facility_id: str
    query: str
    response: Literal["yes", "no"]
    signature: str
    latency_ms: int


class OutcomeFeedback(BaseModel):
    feedback_id: str = ""                    # auto-fill in /outcome handler if empty
    transaction_id: Optional[str] = None     # null for NGO ping without booking
    patient_id: str
    facility_id: str
    factor: Literal["bed", "oxygen", "drug", "specialist"]
    actual_value: float                      # 1.0 / 0.5 / 0.0 — DDL is DOUBLE, not bool
    llm_predicted: Optional[float] = None
    source: Literal["sms", "voice", "nurse_note", "ngo_visit"] = "sms"
    notes: Optional[str] = None
    ts: datetime                             # ISO8601 → datetime, not str


class ReasoningPanelEvent(BaseModel):
    agent: Literal["triage", "extractor", "validator", "router", "transfer", "stream_tick"]
    token: str
    trace_id: str
    ts: datetime


class TriageOutput(BaseModel):
    specialty: str
    urgency: int = Field(ge=1, le=5)  # 1 (low) → 5 (life-threatening); reject hallucinated 99
    confidence: float = Field(ge=0.0, le=1.0)
    required_bed_type: Literal["icu", "hdu", "general", "pediatric", "maternity", "isolation"]
    fast_path: bool
    red_flag_match: list[str] = Field(default_factory=list)
    reasoning: str
