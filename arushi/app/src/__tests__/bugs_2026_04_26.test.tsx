// Negative regression tests for bugs #104, #105, #112 (frontend / api.ts).
//
// Each test is RED on today's code and should flip GREEN when the
// corresponding bug is fixed. Do not fix bugs in this file.
//
//   #104 — reserve() swallows 429; returns generic copy instead of a
//           rate-limit specific reason.
//   #105 — /recommend network failure silently falls back to mocks with
//           only a small banner (no prominent aria-live region).
//   #112 — Schema mismatch: backend sends `hospital_id` (RankedHospital)
//           but CanonicalHospital type uses `facility_id`. adaptHospitals
//           must handle a pure `hospital_id`-shaped response without throwing.

import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { cleanup } from "@testing-library/react";

// Replicate the leaflet stubs so module-level imports inside api.ts / adapter
// don't crash in jsdom.
class FakeDivIcon {
  constructor(_opts?: unknown) {
    /* no-op */
  }
}
const leafletStub = {
  DivIcon: FakeDivIcon,
  Icon: Object.assign(
    function FakeIcon() {
      /* no-op */
    },
    { Default: { mergeOptions: () => undefined, prototype: {} } },
  ),
  divIcon: (opts?: unknown) => new FakeDivIcon(opts),
  latLng: (lat: number, lng: number) => ({ lat, lng }),
  latLngBounds: () => {
    const bounds = {
      extend: () => bounds,
      isValid: () => true,
      pad: () => bounds,
    };
    return bounds;
  },
};
vi.mock("leaflet", () => ({
  default: leafletStub,
  ...leafletStub,
}));
vi.mock("react-leaflet", () => ({
  MapContainer: ({ children }: { children?: React.ReactNode }) => <div data-testid="map">{children}</div>,
  TileLayer: () => null,
  Marker: ({ children }: { children?: React.ReactNode }) => <div>{children}</div>,
  Tooltip: ({ children }: { children?: React.ReactNode }) => <div>{children}</div>,
  useMap: () => ({
    flyTo: () => undefined,
    setView: () => undefined,
    fitBounds: () => undefined,
  }),
}));
vi.mock("../hooks/useSpeechRecognition", () => ({
  useSpeechRecognition: () => ({
    supported: false,
    listening: false,
    transcript: "",
    error: null,
    start: () => undefined,
    stop: () => undefined,
  }),
}));

afterEach(() => {
  cleanup();
  vi.resetModules();
  vi.restoreAllMocks();
});

// ---------------------------------------------------------------------------
// Bug #104 — 429 not handled in reserve(): sixth click returns generic copy
// ---------------------------------------------------------------------------
describe("bug_104_reserve_429_shows_rate_limit_reason", () => {
  beforeEach(() => {
    // Stub the canonical api module so reserve() hits the real error-handling
    // path but the underlying book() call returns a 429.
    vi.doMock("../api", () => {
      const { ApiError } = vi.importActual<typeof import("../api")>("../api") as {
        ApiError: new (msg: string, status: number) => Error & { status: number };
      };
      class FakeApiError extends Error {
        status: number;
        constructor(msg: string, status: number) {
          super(msg);
          this.status = status;
        }
      }
      return {
        HAS_REAL_BACKEND: true,
        ApiError: FakeApiError,
        api: {
          book: vi.fn(async () => {
            throw new FakeApiError("Too Many Requests", 429);
          }),
          recommend: vi.fn(async () => ({
            hospitals: [],
            validator_status: "skipped",
            agreement: null,
          })),
          ngoData: vi.fn(async () => ({ underservedPins: [], deadZones: [] })),
        },
      };
    });
  });

  test("reserve() on 429 should return an errorReason that mentions rate-limiting, not a generic fallback", async () => {
    const { reserve } = await import("../lib/api");

    // The current implementation re-throws the ApiError on 429 — the caller
    // catches it and renders "Reservation failed. Please retry." (generic copy).
    // The fix should convert the 429 into a resolved ReserveResponse whose
    // errorReason contains "too many" or "rate limit".
    let result: Awaited<ReturnType<typeof reserve>> | undefined;
    let caught: unknown;
    try {
      result = await reserve({ hospitalId: "HOSP_01" });
    } catch (e) {
      caught = e;
    }

    // If it throws (current buggy behavior), the UI can only show generic copy.
    // A fixed implementation should NOT throw — it should return a response.
    expect(
      caught,
      `Bug #104: reserve() threw instead of returning a user-friendly 429 response.\n` +
        `The UI falls back to "Reservation failed. Please retry." (generic copy).`,
    ).toBeUndefined();

    // Even if we get a result, the errorReason must be rate-limit specific.
    const reason = (result?.errorReason ?? "").toLowerCase();
    const isTooMany = /too many|rate.?limit|slow down|retry.?after/i.test(reason);
    expect(
      isTooMany,
      `Bug #104: errorReason "${result?.errorReason}" is not rate-limit specific.\n` +
        `Expected something like "Too many bookings" or "Rate limit exceeded".`,
    ).toBe(true);
  });
});

// ---------------------------------------------------------------------------
// Bug #105 — Silent mock fallback: /recommend failure shows tiny banner only
// ---------------------------------------------------------------------------
describe("bug_105_recommend_fallback_shows_prominent_banner", () => {
  beforeEach(() => {
    // Make every fetch() reject so the real-backend path always throws and
    // recommend() falls back to mock data (sets _degraded = true).
    vi.stubGlobal(
      "fetch",
      vi.fn(() => Promise.reject(new Error("network down"))),
    );
    // Also stub the canonical api module so HAS_REAL_BACKEND=true triggers the
    // try-catch-fallback branch in lib/api.ts recommend().
    vi.doMock("../api", () => {
      class FakeApiError extends Error {
        status: number;
        constructor(msg: string, status: number) {
          super(msg);
          this.status = status;
        }
      }
      return {
        HAS_REAL_BACKEND: true,
        ApiError: FakeApiError,
        api: {
          recommend: vi.fn(async () => {
            throw new Error("network down");
          }),
          book: vi.fn(),
          ngoData: vi.fn(async () => ({ underservedPins: [], deadZones: [] })),
        },
      };
    });
  });

  test("after /recommend fails, UI renders a prominent degraded-mode indicator (not just a small banner)", async () => {
    // Import recommend() AFTER the mock is set so it picks up the stub.
    const { recommend, isDegraded } = await import("../lib/api");

    // Trigger a recommend — this should set _degraded = true internally.
    try {
      await recommend({ query: "chest pain" });
    } catch {
      // Some error paths rethrow — that's fine, we're testing the degraded flag.
    }

    expect(
      isDegraded(),
      "Bug #105: isDegraded() should return true after a network failure on /recommend",
    ).toBe(true);

    // The real failure mode of #105: even though isDegraded() is true, the UI
    // only renders a small "Demo data" badge. There is no aria-live="assertive"
    // or role="alert" region with a strong/prominent warning.
    // We assert on the spec: when degraded, recommend() should either throw
    // (forcing the component to render an error boundary) OR the caller contract
    // should guarantee a prominent notice. Today it silently returns mock data.
    //
    // Desired: the returned hospitals are clearly flagged as mock / demo data.
    // The function currently returns a RecommendResponse indistinguishable from
    // a live response. Assert that a `_isMock` or `degraded` flag exists in the
    // response (this is the fix target — currently absent).
    let resp: Awaited<ReturnType<typeof recommend>> | undefined;
    try {
      resp = await recommend({ query: "chest pain" });
    } catch {
      // If it throws after the fix that's also acceptable — caught above.
    }

    if (resp !== undefined) {
      const hasDegradedFlag =
        // @ts-expect-error — checking for fix-target field that doesn't exist yet
        resp.degraded === true ||
        // @ts-expect-error
        resp._isMock === true ||
        // @ts-expect-error
        resp.source === "mock";

      expect(
        hasDegradedFlag,
        `Bug #105: recommend() fell back to mocks but returned no machine-readable\n` +
          `degraded/mock flag on the response. The UI can only show a small badge,\n` +
          `not a prominent aria-live banner. Fix: add { degraded: true } to the\n` +
          `mockRecommend return value (or similar contract).`,
      ).toBe(true);
    }
  });
});

// ---------------------------------------------------------------------------
// Bug #112 — Schema mismatch: RankedHospital.hospital_id vs frontend facility_id
// ---------------------------------------------------------------------------
describe("bug_112_schema_mismatch_hospital_id_vs_facility_id", () => {
  test("adaptHospitals accepts a backend RankedHospital-shaped response (hospital_id field) without throwing", async () => {
    const { adaptHospitals } = await import("../lib/adapter");

    // This is exactly the shape contracts/schemas.py RankedHospital serialises to.
    // Note: NO `facility_id` key — only `hospital_id`.
    const backendRow = {
      hospital_id: "HOSP_001",
      name: "Apollo Mumbai",
      travel_min: 12,
      specialty_match: 0.88,
      cost_estimate_inr: 5000,
      non_medical_cost_inr: 500,
      lat: 19.076,
      lon: 72.8777,
    };

    // adaptHospitals should NOT throw — if it does, the UI crashes silently
    // whenever the backend uses the RankedHospital serialization (hospital_id).
    let result: ReturnType<typeof adaptHospitals> | undefined;
    let thrown: unknown;
    try {
      result = adaptHospitals([backendRow]);
    } catch (e) {
      thrown = e;
    }

    expect(
      thrown,
      `Bug #112: adaptHospitals threw when given a { hospital_id } shaped row.\n` +
        `The backend RankedHospital schema uses hospital_id; if the adapter only\n` +
        `handles facility_id it crashes silently at runtime.\nError: ${thrown}`,
    ).toBeUndefined();

    // The adapted hospital's id should be the hospital_id value.
    expect(result).toHaveLength(1);
    expect(result?.[0].id).toBe("HOSP_001");
  });

  test("adaptHospitals rejects a row with neither hospital_id nor facility_id (should throw or return empty)", async () => {
    const { adaptHospitals } = await import("../lib/adapter");

    // A row missing both id fields is a genuine schema mismatch — the adapter
    // should surface this rather than silently producing a broken Hospital.
    const brokenRow = {
      // no hospital_id, no facility_id — pure schema drift
      name: "Ghost Hospital",
      lat: 0,
      lon: 0,
      trust_calibrated: 0.5,
      trust_score: 0.5,
      trust_source: "rule-inferred" as const,
      max_factor_disagreement: null,
      city: "Mumbai",
      state: "MH",
      pincode: "400001",
      facility_type: "Private",
    };

    let result: ReturnType<typeof adaptHospitals> | undefined;
    let thrown: unknown;
    try {
      // @ts-expect-error — intentionally passing broken shape to test runtime guard
      result = adaptHospitals([brokenRow]);
    } catch (e) {
      thrown = e;
    }

    // Either it threw (good) OR it returned a hospital with an empty/undefined id
    // (bad — the bug surface). Assert the id is not empty string or undefined.
    if (!thrown) {
      const id = result?.[0]?.id;
      expect(
        id && id.length > 0,
        `Bug #112: adaptHospitals produced hospital with empty/undefined id "${id}"\n` +
          `when given a row with neither hospital_id nor facility_id.\n` +
          `The adapter should throw or skip the row.`,
      ).toBe(true);
    }
    // If it threw, the guard is working — test passes either way for this shape.
  });
});
