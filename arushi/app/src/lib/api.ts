// Hybrid API client.
// - VITE_PUBLIC_URL set → call canonical FastAPI (Tero+Mubarak), adapt to legacy UI shape.
// - VITE_PUBLIC_URL empty → fall back to local JSON mocks (dev / offline demo).

import { ApiError, api as canonicalApi, HAS_REAL_BACKEND } from "../api";
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
  const data = (await import("../../mocks/hospitals.json")).default as RecommendResponse;
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
// Auth misconfig is a separate signal — distinct from a flaky network — so the
// UI can render "check VITE_DEMO_KEY" instead of "running on cached data".
// Mock fallback would mask a 401/403 and lose hours of debug time at the demo.
let _authError = false;
export const isDegraded = () => _degraded || !HAS_REAL_BACKEND;
export const isBackendConfigured = () => HAS_REAL_BACKEND;
export const hasAuthError = () => _authError;

// crypto.randomUUID is available in modern browsers + Node 19+. The fallback
// only runs in test rigs / older runtimes — Date.now() alone collides on
// rapid double-clicks, hence the random suffix.
function newPatientId(hospitalId: string): string {
  const lower = hospitalId.toLowerCase();
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return `demo_${lower}_${crypto.randomUUID().slice(0, 8)}`;
  }
  const suffix = `${Date.now()}${Math.random().toString(36).slice(2, 8)}`;
  return `demo_${lower}_${suffix}`;
}

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
      const resp = await canonicalApi.recommend({ user_text: query, language: "en" });
      _degraded = false;
      _authError = false;
      let hospitals: Hospital[];
      try {
        hospitals = adaptHospitals(resp.hospitals);
      } catch (adaptErr) {
        // Real backend reachable but returned data we can't reshape — this is
        // a contract bug (schema drift), not a network outage. Surface it loudly
        // instead of pretending mocks are fine.
        _degraded = true;
        // eslint-disable-next-line no-console
        console.error("[api] /recommend returned data adapter could not parse:", adaptErr);
        throw new Error("backend returned invalid hospital data");
      }
      return {
        hospitals,
        validator_status: resp.validator_status,
        agreement: resp.agreement,
      };
    } catch (err) {
      // 401/403 → auth misconfig. Falling back to mocks would silently hide
      // the broken X-Demo-Key during the demo. Rethrow so the boundary catches it.
      if (err instanceof ApiError && (err.status === 401 || err.status === 403)) {
        _authError = true;
        _degraded = true;
        throw err;
      }
      // 429 means the backend is reachable but the demo hit a rate bucket.
      // Do not flip into offline mocks or the UI lies with "Backend unreachable".
      if (err instanceof ApiError && err.status === 429) {
        _degraded = false;
        throw err;
      }
      // Backend reachable but body wasn't JSON — schema drift, surface it.
      if (err instanceof ApiError && err.parse) {
        _degraded = true;
        throw err;
      }
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
    let out;
    try {
      const patient_id = newPatientId(request.hospitalId);
      // Let real infrastructure failures propagate — UI shows the rollback
      // animation + banner. Auth/config errors are a known demo setup failure,
      // so convert them into a visible rollback reason instead of generic copy.
      out = await canonicalApi.book(request.hospitalId, patient_id);
    } catch (err) {
      if (err instanceof ApiError && (err.status === 401 || err.status === 403)) {
        _degraded = true;
        _authError = true;
        return {
          success: false,
          referenceId: null,
          status: "REJECTED",
          reason: "Missing or invalid demo key. Set VITE_DEMO_KEY to match the backend DEMO_KEY.",
          commit_error: null,
          transaction_id: null,
          errorReason: "Missing or invalid demo key. Set VITE_DEMO_KEY to match the backend DEMO_KEY.",
        };
      }
      throw err;
    }
    _degraded = false;
    _authError = false;
    const committed = out.status === "COMMITTED";
    // When the saga did NOT commit, surface a `null` referenceId so the UI
    // never renders a fabricated "RSV-{id}-FAILED" string as a real reservation
    // code. The errorReason field carries the human-friendly summary.
    const errorReason = committed
      ? null
      : out.reason ?? out.commit_error ?? `Reservation ${out.status.toLowerCase()}`;
    return {
      success: committed,
      referenceId: committed ? out.transaction_id ?? null : null,
      status: out.status,
      reason: out.reason,
      // Normalize undefined → null so consumers can `?? "—"` cleanly.
      commit_error: out.commit_error ?? null,
      transaction_id: out.transaction_id ?? null,
      errorReason,
    };
  }

  const referenceId = `RSV-${request.hospitalId.toUpperCase()}-${Date.now().toString().slice(-6)}`;
  await delay(650);
  return {
    success: true,
    referenceId,
    status: "COMMITTED",
    transaction_id: referenceId,
    commit_error: null,
    errorReason: null,
  };
}

export async function streamReasoning(
  onToken: (msgId: string, token: string, done: boolean) => void,
): Promise<void> {
  // Mock-only: drives the legacy ReasoningPanel rows-prop UI. For real SSE
  // against /sse use ReasoningPanelSSE component (canonical event vocab).
  const data = (await import("../../mocks/reasoning.json")).default as ReasoningMessage[];

  for (const message of data) {
    for (let i = 0; i < message.tokens.length; i += 1) {
      await delay(85);
      onToken(message.id, message.tokens[i], i === message.tokens.length - 1);
    }
  }
}

export async function getDoctorCopilotData(): Promise<DoctorCopilotData> {
  await delay(260);
  return (await import("../../mocks/doctor-copilot.json")).default as DoctorCopilotData;
}

export async function getNGODashboardData(): Promise<NGODashboardData> {
  if (HAS_REAL_BACKEND) {
    try {
      const data = await canonicalApi.ngoData();
      if (!data || !Array.isArray(data.underservedPins) || !Array.isArray(data.deadZones)) {
        throw new Error("backend returned invalid NGO data shape");
      }
      return data;
    } catch (err) {
      if (err instanceof ApiError && (err.status === 401 || err.status === 403)) {
        _authError = true;
        _degraded = true;
        throw err;
      }
      // NGO data is an optional dashboard feed. Its fallback should not flip
      // the global patient-flow degraded banner when /recommend is healthy.
      // eslint-disable-next-line no-console
      console.warn("[api] /ngo-data failed, falling back to mocks:", err);
    }
  }
  await delay(260);
  return (await import("../../mocks/ngo-dashboard.json")).default as NGODashboardData;
}
