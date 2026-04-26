import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

describe("api degraded state", () => {
  beforeEach(() => {
    vi.resetModules();
    vi.stubEnv("VITE_PUBLIC_URL", "https://api.example.test");
  });

  afterEach(() => {
    vi.unstubAllEnvs();
    vi.restoreAllMocks();
  });

  test("ngo fallback does not poison the patient-flow degraded banner", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        const url = String(input);
        if (url.endsWith("/ngo-data")) {
          return new Response("not found", { status: 404 });
        }
        if (url.endsWith("/recommend")) {
          return Response.json({
            triage: {
              specialty: "Trauma",
              urgency: 5,
              confidence: 0.9,
              required_bed_type: "icu",
              fast_path: true,
              red_flag_match: [],
              reasoning: "test",
            },
            hospitals: [
              {
                facility_id: "HOSP_TEST",
                name: "Test General",
                city: "Mumbai",
                state: "MH",
                pincode: "400001",
                facility_type: "hospital",
                lat: 19.08,
                lon: 72.88,
                trust_score: 0.91,
                trust_calibrated: 0.9,
                trust_source: "two-model-verified",
                max_factor_disagreement: null,
              },
            ],
            fast_path: true,
            validator_status: "ok",
            agreement: true,
          });
        }
        return new Response("unexpected url", { status: 500 });
      }),
    );

    const { getNGODashboardData, isDegraded, recommend } = await import("../lib/api");

    await getNGODashboardData();
    expect(isDegraded()).toBe(false);

    await expect(recommend({ query: "critical trauma" })).resolves.toMatchObject({
      hospitals: [{ id: "HOSP_TEST" }],
    });
    expect(isDegraded()).toBe(false);
  });

  test("live railway recommend shape adapts without entering degraded mode", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        const url = String(input);
        if (url.endsWith("/recommend")) {
          return Response.json({
            triage: {
              specialty: "emergency medicine",
              urgency: 1,
              confidence: 0.5,
              required_bed_type: "general",
              fast_path: false,
              red_flag_match: [],
              reasoning: "test",
            },
            hospitals: [
              {
                hospital_id: "5392",
                name: "Highway Medical Centre | Dr. Hemant Dugad",
                travel_min: 12,
                specialty_match: 1,
                cost_estimate_inr: 4000,
                non_medical_cost_inr: 90,
                lat: 19.126594543457,
                lon: 72.8575134277343,
              },
            ],
            fast_path: false,
          });
        }
        return new Response("unexpected url", { status: 500 });
      }),
    );

    const { isDegraded, recommend } = await import("../lib/api");

    await expect(recommend({ query: "critical care nearby" })).resolves.toMatchObject({
      hospitals: [
        {
          id: "5392",
          name: "Highway Medical Centre | Dr. Hemant Dugad",
          etaMinutes: 12,
          demoted: false,
        },
      ],
      validator_status: undefined,
    });
    expect(isDegraded()).toBe(false);
  });
});
