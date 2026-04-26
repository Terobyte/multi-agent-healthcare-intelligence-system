// Canonical API client — talks to the real FastAPI backend (Tero+Mubarak).
// Field names match app/schemas.py exactly. Use lib/adapter.ts to convert
// CanonicalHospital → legacy Hospital for existing UI components.

import type {
  BookingOutput,
  CanonicalRecommendResponse,
  HealthResponse,
  OutcomeFeedback,
  TriageOutput,
} from "./lib/types";

const BASE = (import.meta.env.VITE_PUBLIC_URL ?? "").replace(/\/+$/, "");
const DEMO_KEY = import.meta.env.VITE_DEMO_KEY ?? "";

export const API_BASE = BASE;
export const HAS_REAL_BACKEND = BASE.length > 0;

if (!HAS_REAL_BACKEND) {
  // eslint-disable-next-line no-console
  console.warn(
    "[api] VITE_PUBLIC_URL not set — canonical api.ts disabled, lib/api.ts falls back to mocks.",
  );
}

type Method = "GET" | "POST";
interface CallOpts {
  mutating?: boolean;
  signal?: AbortSignal;
}

async function call<T>(
  method: Method,
  path: string,
  body?: unknown,
  opts: CallOpts = {},
): Promise<T> {
  if (!HAS_REAL_BACKEND) {
    throw new Error(
      `[api] cannot call ${path} — VITE_PUBLIC_URL is empty. Set it in arushi/app/.env.local.`,
    );
  }
  const headers: Record<string, string> = { "content-type": "application/json" };
  if (opts.mutating && DEMO_KEY) headers["X-Demo-Key"] = DEMO_KEY;
  const r = await fetch(`${BASE}${path}`, {
    method,
    headers,
    body: body == null ? undefined : JSON.stringify(body),
    signal: opts.signal,
  });
  if (!r.ok) {
    const text = await r.text().catch(() => "");
    throw new Error(`${method} ${path} → ${r.status} ${text.slice(0, 200)}`);
  }
  return (await r.json()) as T;
}

export const api = {
  health: (signal?: AbortSignal) =>
    call<HealthResponse>("GET", "/health", undefined, { signal }),
  triage: (user_text: string, language_hint = "en", signal?: AbortSignal) =>
    call<TriageOutput>("POST", "/triage", { user_text, language_hint }, { signal }),
  recommend: (user_text: string, language_hint = "en", signal?: AbortSignal) =>
    call<CanonicalRecommendResponse>(
      "POST",
      "/recommend",
      { user_text, language_hint },
      { signal },
    ),
  book: (facility_id: string, patient_id: string, signal?: AbortSignal) =>
    call<BookingOutput>(
      "POST",
      "/book",
      { facility_id, patient_id },
      { mutating: true, signal },
    ),
  outcome: (fb: OutcomeFeedback, signal?: AbortSignal) =>
    call<{ status: string; feedback_id: string }>(
      "POST",
      "/outcome",
      fb,
      { mutating: true, signal },
    ),
};

// SSE URLs — EventSource cannot send custom headers, so /sse stays open
// (Tero Block 35c protects /book + /outcome via X-Demo-Key, not /sse).
export const SSE_URL = (sessionId: string) =>
  `${BASE}/sse?session_id=${encodeURIComponent(sessionId)}`;

export const SSE_DEMO_URL = (sessionId: string) =>
  `${BASE}/sse_demo?session_id=${encodeURIComponent(sessionId)}`;
