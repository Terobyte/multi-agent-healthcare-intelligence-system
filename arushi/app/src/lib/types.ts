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
