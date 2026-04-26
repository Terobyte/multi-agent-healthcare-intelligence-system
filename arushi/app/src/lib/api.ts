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

async function mockRecommend(query: string): Promise<RecommendResponse> {
  await delay(420);
  const data = (await import("../../../mocks/hospitals.json")).default as RecommendResponse;
  const hospitals = [...data.hospitals].sort(
    (a, b) => scoreHospitalForQuery(b, query) - scoreHospitalForQuery(a, query),
  );
  return { hospitals };
}

// Sticky flag — flips to true on the first failed real-backend call so the UI
// can surface "demo data only" instead of silently lying. Stays sticky until a
// successful real call clears it (so a flapping connection doesn't strobe).
// When HAS_REAL_BACKEND is false the app is degraded by definition, so we
// surface that synchronously — without it, the banner only appears after the
// first recommend() round-trips, which is too late for the user.
let _degraded = false;
export const isDegraded = () => _degraded || !HAS_REAL_BACKEND;

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
    try {
      const resp = await canonicalApi.recommend(query);
      _degraded = false;
      return { hospitals: adaptHospitals(resp.hospitals) };
    } catch (err) {
      _degraded = true;
      // eslint-disable-next-line no-console
      console.warn("[api] /recommend failed, falling back to mocks:", err);
      return mockRecommend(query);
    }
  }

  // No real backend wired up — that IS degraded mode by definition. Without
  // this flag the UI silently shows fake hospitals as if they were live data.
  _degraded = true;
  return mockRecommend(query);
}

export async function reserve(request: ReserveRequest): Promise<ReserveResponse> {
  if (HAS_REAL_BACKEND) {
    const patient_id = `demo_${request.hospitalId.toLowerCase()}_${Date.now().toString().slice(-6)}`;
    // Let real failures propagate — UI shows the rollback animation + banner.
    // Lying about success here would let the stage demo pass while production
    // saga rolled back, which is much worse than an honest red tile.
    const out = await canonicalApi.book(request.hospitalId, patient_id);
    _degraded = false;
    return {
      success: out.status === "COMMITTED",
      referenceId: out.transaction_id ?? `RSV-${request.hospitalId}-FAILED`,
      status: out.status,
      reason: out.reason,
      commit_error: out.commit_error,
      transaction_id: out.transaction_id,
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
