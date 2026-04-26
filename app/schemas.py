from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


# Stricter validation across the board:
# - max_length on every str field — caps payload size, blunts log-injection /
#   memory-exhaustion vectors before they reach Databricks.
# - lat/lon clamped to physical earth ranges; trust/confidence clamped to [0,1].
# - extra="forbid" on every model — unknown fields raise rather than silently
#   drop, so a frontend / agent contract drift surfaces as a 422 not as a
#   ghost field that disappears in transit.
class Hospital(BaseModel):
    model_config = ConfigDict(extra="forbid")

    facility_id: str = Field(max_length=64)
    name: str = Field(max_length=120)
    city: str = Field(max_length=80)
    state: str = Field(max_length=80)
    pincode: str = Field(max_length=10)
    facility_type: str = Field(max_length=40)
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    trust_score: float = Field(ge=0.0, le=1.0)            # gold_trust_final.trust_score
    trust_calibrated: float = Field(ge=0.0, le=1.0)       # v_trust_calibrated.trust_calibrated
    trust_source: Literal["two-model-verified", "models-disagree", "llm-verified", "rule-inferred"]
    max_factor_disagreement: Optional[float] = Field(default=None, ge=0.0, le=1.0)


class FactorWithReasoning(BaseModel):
    model_config = ConfigDict(extra="forbid")

    value: float
    reasoning: str = Field(max_length=2000)
    source: str = Field(max_length=200)


class TrustScorerOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    facility_id: str = Field(max_length=64)
    factors: dict[str, FactorWithReasoning] = Field(max_length=32)
    trust: float = Field(ge=0.0, le=1.0)
    trust_calibrated: float = Field(ge=0.0, le=1.0)
    extractor_reasoning: str = Field(max_length=2000)
    validator_reasoning: str = Field(max_length=2000)
    agreement: bool


class BookingOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    transaction_id: Optional[str] = Field(default=None, max_length=2000)   # None if REJECTED before insert
    status: Literal["COMMITTED", "ROLLED_BACK", "REJECTED"]
    resources: dict[str, str] = Field(max_length=16)
    facility_id: str = Field(max_length=64)
    reason: Optional[str] = Field(default=None, max_length=200)            # human-readable reason for REJECTED/ROLLED_BACK
    commit_error: Optional[str] = Field(default=None, max_length=500)      # set when children OK but parent COMMIT update raised


class IntakeHandshake(BaseModel):
    model_config = ConfigDict(extra="forbid")

    facility_id: str = Field(max_length=64)
    query: str = Field(max_length=2000)
    response: Literal["yes", "no"]
    signature: str = Field(max_length=2000)
    latency_ms: int = Field(ge=0, le=2_147_483_647)


class OutcomeFeedback(BaseModel):
    model_config = ConfigDict(extra="forbid")

    feedback_id: Optional[str] = Field(default=None, max_length=64)        # auto-fill in /outcome handler if empty
    transaction_id: Optional[str] = Field(default=None, max_length=2000)   # null for NGO ping without booking
    patient_id: str = Field(max_length=64)
    facility_id: str = Field(max_length=64)
    factor: Literal["bed", "oxygen", "drug", "specialist"]
    actual_value: float = Field(ge=0.0, le=1.0)                            # 1.0 / 0.5 / 0.0 — DDL is DOUBLE, not bool
    llm_predicted: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    source: Literal["sms", "voice", "nurse_note", "ngo_visit"] = "sms"
    notes: Optional[str] = Field(default=None, max_length=2000)
    ts: datetime                             # ISO8601 → datetime, not str


class ReasoningPanelEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    agent: Literal["triage", "extractor", "validator", "router", "transfer", "stream_tick"]
    token: str = Field(max_length=2000)
    trace_id: str = Field(max_length=64)
    ts: datetime


class TriageOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    specialty: str = Field(max_length=64)
    urgency: int = Field(ge=1, le=5)  # 1 (low) → 5 (life-threatening); reject hallucinated 99
    confidence: float = Field(ge=0.0, le=1.0)
    required_bed_type: Literal["icu", "hdu", "general", "pediatric", "maternity", "isolation"]
    fast_path: bool
    red_flag_match: list[str] = Field(default_factory=list, max_length=20)
    reasoning: str = Field(max_length=2000)
