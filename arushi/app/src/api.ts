// Canonical API client — talks to the real FastAPI backend (Tero+Mubarak).
// Field names match app/schemas.py exactly. Use lib/adapter.ts to convert
// CanonicalHospital → legacy Hospital for existing UI components.

import type {
  BookingOutput,
  CanonicalRecommendResponse,
  HealthResponse,
  NGODashboardData,
  OutcomeFeedback,
  TriageOutput,
} from "./lib/types";

const BASE = (import.meta.env.VITE_PUBLIC_URL || "").replace(/\/+$/, "");
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

// Hardened HTTP error subclass — carries .status so lib/api.ts can distinguish
// 401/403 (auth misconfig — surface, do NOT silently fall back to mocks) from
// network/5xx (acceptable mock fallback). `parse: true` flags JSON-shape issues
// from a real backend (rethrow as backend-data-bug, not a network outage).
export class ApiError extends Error {
  status: number;
  parse: boolean;
  constructor(message: string, status: number, parse = false) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.parse = parse;
  }
}

// 30s ceiling — long enough for cold Databricks warehouse warmup, short enough
// that a hung pod doesn't stall the demo's recommend() spinner indefinitely.
const FETCH_TIMEOUT_MS = 30000;

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
  if (opts.mutating) {
    if (!DEMO_KEY) {
      throw new ApiError(
        "missing VITE_DEMO_KEY for mutating request",
        401,
      );
    }
    headers["X-Demo-Key"] = DEMO_KEY;
  }

  // Compose caller-provided AbortSignal with our timeout — abort on whichever
  // fires first. Cleared in `finally` so the timer can't fire on a finished call.
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), FETCH_TIMEOUT_MS);
  if (opts.signal) {
    if (opts.signal.aborted) controller.abort();
    else opts.signal.addEventListener("abort", () => controller.abort(), { once: true });
  }

  const url = `${BASE}${path}`;
  try {
    const r = await fetch(url, {
      method,
      headers,
      body: body == null ? undefined : JSON.stringify(body),
      signal: controller.signal,
    });
    if (!r.ok) {
      const text = await r.text().catch(() => "");
      // Slice to 100 chars and prefix so callers don't render raw backend traces
      // (which could leak stack frames / SQL fragments) as user-visible text.
      throw new ApiError(
        `upstream error: ${method} ${path} → ${r.status} ${text.slice(0, 100)}`,
        r.status,
      );
    }
    try {
      return (await r.json()) as T;
    } catch {
      // 2xx with malformed body — backend bug, not a network outage. lib/api.ts
      // checks .parse to decide whether to surface vs fall back to mocks.
      throw new ApiError(`backend returned invalid JSON at ${url}`, 200, true);
    }
  } finally {
    clearTimeout(timeout);
  }
}

export const api = {
  health: (signal?: AbortSignal) =>
    call<HealthResponse>("GET", "/health", undefined, { signal }),
  triage: (user_text: string, language_hint = "en", signal?: AbortSignal) =>
    call<TriageOutput>("POST", "/triage", { user_text, language_hint }, { signal }),
  recommend: (req: { user_text: string; language?: string }, signal?: AbortSignal) =>
    call<CanonicalRecommendResponse>(
      "POST",
      "/recommend",
      { user_text: req.user_text, language: req.language ?? "en" },
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
  ngoData: (signal?: AbortSignal) =>
    call<NGODashboardData>("GET", "/ngo-data", undefined, { signal }),
  // Sponsor route — Databricks Genie passthrough. Returns natural-language
  // answer + generated SQL + table rows when SPONSOR_GENIE_LIVE=true on the
  // backend, or canned demo data otherwise. Marked mutating so the X-Demo-Key
  // header is sent (route is auth-gated on the backend).
  genie: (
    query: string,
    conversation_id?: string,
    signal?: AbortSignal,
  ) =>
    call<GenieResponse>(
      "POST",
      "/sponsor/genie/query",
      { query, conversation_id: conversation_id ?? null },
      { mutating: true, signal },
    ),
};

export interface GenieResponse {
  conversation_id: string | null;
  sql: string;
  columns?: string[];
  rows: Array<Array<string | number | boolean | null>>;
  explanation: string;
  source: "live" | "canned";
}

// SSE URLs — EventSource cannot send custom headers, so /sse stays open
// (Tero Block 35c protects /book + /outcome via X-Demo-Key, not /sse).
export const SSE_URL = (sessionId: string) =>
  `${BASE}/sse?session_id=${encodeURIComponent(sessionId)}`;

export const SSE_DEMO_URL = (sessionId: string) =>
  `${BASE}/sse_demo?session_id=${encodeURIComponent(sessionId)}`;
