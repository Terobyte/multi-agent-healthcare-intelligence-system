// Hybrid API client.
// - VITE_PUBLIC_URL set → call canonical FastAPI (Tero+Mubarak), adapt to legacy UI shape.
// - VITE_PUBLIC_URL empty → fall back to local JSON mocks (dev / offline demo).

import { api as canonicalApi, HAS_REAL_BACKEND } from "../api";
import { adaptHospitals } from "./adapter";
import type {
  DoctorCopilotData,
  Hospital,
  NGODashboardData,
  ReasoningMessage,
  RecommendRequest,
  RecommendResponse,
  ReserveRequest,
  ReserveResponse,
} from "./types";

const delay = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

const scoreHospitalForQuery = (hospital: Hospital, query: string) => {
  const normalized = query.toLowerCase();
  const emergencyBoost =
    normalized.includes("critical") || normalized.includes("trauma") || normalized.includes("urgent")
      ? 12
      : 0;
  const oxygenScore = hospital.trustSignals.find((signal) => signal.kind === "Oxygen")?.score ?? 0;
  const specialistScore =
    hospital.trustSignals.find((signal) => signal.kind === "Specialist")?.score ?? 0;
  const trustComposite = (oxygenScore + specialistScore) * 40;
  const etaPenalty = hospital.etaMinutes * 0.9;
  const distancePenalty = hospital.distanceKm * 0.7;
  const demotionPenalty = hospital.demoted ? 18 : 0;
  return trustComposite + emergencyBoost - etaPenalty - distancePenalty - demotionPenalty;
};

export async function recommend(request: RecommendRequest): Promise<RecommendResponse> {
  const query = request.query.trim();
  const lower = query.toLowerCase();
  if (lower.includes("simulate error")) {
    throw new Error("Mock recommendation service unavailable");
  }
  if (lower.includes("no match")) {
    return { hospitals: [] };
  }

  if (HAS_REAL_BACKEND) {
    const resp = await canonicalApi.recommend(query);
    return { hospitals: adaptHospitals(resp.hospitals) };
  }

  await delay(420);
  const data = (await import("../../../mocks/hospitals.json")).default as RecommendResponse;
  const hospitals = [...data.hospitals].sort(
    (a, b) => scoreHospitalForQuery(b, query) - scoreHospitalForQuery(a, query),
  );
  return { hospitals };
}

export async function reserve(request: ReserveRequest): Promise<ReserveResponse> {
  if (HAS_REAL_BACKEND) {
    const patient_id = `demo_${request.hospitalId.toLowerCase()}_${Date.now().toString().slice(-6)}`;
    const out = await canonicalApi.book(request.hospitalId, patient_id);
    return {
      success: out.status === "COMMITTED",
      referenceId: out.transaction_id ?? `RSV-${request.hospitalId}-FAILED`,
    };
  }

  await delay(650);
  return {
    success: true,
    referenceId: `RSV-${request.hospitalId.toUpperCase()}-${Date.now().toString().slice(-6)}`,
  };
}

export async function streamReasoning(
  onToken: (msgId: string, token: string, done: boolean) => void,
): Promise<void> {
  // Mock-only: drives the legacy ReasoningPanel rows-prop UI. For real SSE
  // against /sse use ReasoningPanelSSE component (canonical event vocab).
  const data = (await import("../../../mocks/reasoning.json")).default as ReasoningMessage[];

  for (const message of data) {
    for (let i = 0; i < message.tokens.length; i += 1) {
      await delay(85);
      onToken(message.id, message.tokens[i], i === message.tokens.length - 1);
    }
  }
}

export async function getDoctorCopilotData(): Promise<DoctorCopilotData> {
  await delay(260);
  return (await import("../../../mocks/doctor-copilot.json")).default as DoctorCopilotData;
}

export async function getNGODashboardData(): Promise<NGODashboardData> {
  await delay(260);
  return (await import("../../../mocks/ngo-dashboard.json")).default as NGODashboardData;
}
