// =============================================================================
// LEGACY UI TYPES (used by existing components — Hospital camelCase shape).
// Kept stable so PatientFlow / DoctorCopilot / NGODashboard don't break.
// New code should prefer the canonical types below and convert via lib/adapter.
// =============================================================================

export type TrustKind = "Bed" | "Oxygen" | "Drug" | "Specialist";

export interface TrustEvidence {
  summary: string;
  lastUpdatedAt?: string;
  method?: string;
  sourceId?: string;
}

export interface TrustSignal {
  kind: TrustKind;
  score: number;
  ci: number;
  source: string;
  evidence?: TrustEvidence;
}

export interface Hospital {
  id: string;
  name: string;
  lat: number;
  lng: number;
  distanceKm: number;
  etaMinutes: number;
  demoted?: boolean;
  trustSignals: TrustSignal[];
}

export interface RecommendRequest {
  query: string;
}

export interface RecommendResponse {
  hospitals: Hospital[];
}

export interface ReserveRequest {
  hospitalId: string;
}

export interface ReserveResponse {
  success: boolean;
  referenceId: string;
}

export interface ReasoningMessage {
  id: string;
  agent: "Routing Agent" | "Risk Agent" | "Verification Agent";
  tokens: string[];
}

export interface DoctorCopilotData {
  sendingHospitalId: string;
  receivingHospitalIds: string[];
  referralPreview: {
    patientTag: string;
    priority: "Low" | "Medium" | "High";
    notes: string;
  };
  ambulanceEtaMinutes: number;
}

export interface NGOPin {
  id: string;
  pin: string;
  specialty: string;
  severity: "low" | "medium" | "high";
  lat: number;
  lng: number;
  populationGap: number;
}

export interface NGODeadZone {
  id: string;
  label: string;
  description: string;
}

export interface NGODashboardData {
  specialties: string[];
  underservedPins: NGOPin[];
  deadZones: NGODeadZone[];
}

// =============================================================================
// CANONICAL BACKEND TYPES (mirror app/schemas.py — Tero+Mubarak shipped).
// Used by src/api.ts. Field names must match Pydantic exactly; drift breaks
// /book + /trace + /sse contracts.
// =============================================================================

export type TrustSource =
  | "two-model-verified"
  | "models-disagree"
  | "llm-verified"
  | "rule-inferred";

export interface CanonicalHospital {
  facility_id: string;
  name: string;
  city: string;
  state: string;
  pincode: string;
  facility_type: string;
  lat: number;
  lon: number;
  trust_score: number;
  trust_calibrated: number;
  trust_source: TrustSource;
  max_factor_disagreement: number | null;
}

export interface TriageOutput {
  specialty: string;
  urgency: number;
  confidence: number;
  required_bed_type: "icu" | "hdu" | "general" | "pediatric" | "maternity" | "isolation";
  fast_path: boolean;
  red_flag_match: string[];
  reasoning: string;
}

export interface CanonicalRecommendResponse {
  triage: TriageOutput;
  hospitals: CanonicalHospital[];
  fast_path: boolean;
}

export interface BookingOutput {
  transaction_id: string | null;
  status: "COMMITTED" | "ROLLED_BACK" | "REJECTED";
  resources: Record<string, string>;
  facility_id: string;
  reason?: string | null;
  // Surfaced by app/agents/booking.py when the parent COMMITTED-update fails
  // mid-saga; UI can show the partial-commit warning instead of plain error.
  commit_error?: string | null;
}

export interface OutcomeFeedback {
  feedback_id?: string;
  transaction_id?: string | null;
  patient_id: string;
  facility_id: string;
  factor: "bed" | "oxygen" | "drug" | "specialist";
  actual_value: number;
  llm_predicted?: number | null;
  source?: "sms" | "voice" | "nurse_note" | "ngo_visit";
  notes?: string | null;
  ts: string;
}

export interface ReasoningPanelEvent {
  agent: "triage" | "extractor" | "validator" | "router" | "transfer" | "stream_tick";
  token: string;
  trace_id: string;
  ts: string;
}

export interface HealthResponse {
  status: "ok" | "degraded";
  fm_ok: boolean;
  fm_endpoints: number | null;
  warehouse: string;
}
