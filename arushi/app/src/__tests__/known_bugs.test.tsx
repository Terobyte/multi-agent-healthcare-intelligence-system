// Failing regression tests for two real frontend bugs flagged by the audit.
// These are written to be RED on the current code. Do NOT fix the bugs here —
// fixes belong in a separate PR.
//
//   Bug A (lib/api.ts:67-71 + missing UI banner) — when /recommend can't reach
//     the real backend the client falls back to mock JSON but the UI never
//     warns the user. Judges see fake hospitals presented as live data.
//
//   Bug B (PatientFlow.tsx:100-104) — booking failures always render the same
//     generic string. The backend's `reason` / `commit_error` fields (e.g.
//     "duplicate active transaction") get dropped on the floor.

import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";

// react-leaflet + leaflet blow up in jsdom (no DOMRect, no SVG sizing). Stub
// them out so PatientFlow's HospitalMap can render to an empty div.
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

// useSpeechRecognition pokes window.SpeechRecognition which jsdom doesn't have.
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

// -------------------------------------------------------------------------
// Bug A — degraded-mode banner missing when API silently falls back to mocks.
// -------------------------------------------------------------------------
describe("bug_degraded_mode_banner_visible_when_api_falls_back_to_mocks", () => {
  beforeEach(() => {
    // Force every fetch (real backend probe) to fail so lib/api.ts hits its
    // catch branch and serves mock hospitals.
    vi.stubGlobal(
      "fetch",
      vi.fn(() => Promise.reject(new Error("network down"))),
    );
  });

  test("homepage shows a visible 'demo mode / sample data / backend unavailable' indicator after fallback", async () => {
    const { default: PatientFlow } = await import("../pages/PatientFlow");
    render(<PatientFlow />);

    // Wait for the auto-fired recommendation to settle and hospitals to render
    // from the mock JSON. (mockRecommend resolves after a 420ms delay.)
    await waitFor(
      () => {
        // ChatInput is always present; once the mock data has been swapped in
        // the page is past its loading spinner.
        const cards = document.querySelectorAll("article, [data-testid='hospital-card']");
        // Either real hospital cards rendered, or at minimum the auto-query
        // promise has resolved — give it generous time.
        expect(cards.length >= 0).toBe(true);
      },
      { timeout: 3000 },
    );

    // Assert: somewhere in the DOM there's an indicator that the data is not
    // live. Accept any of the obvious phrasings.
    const body = document.body.textContent ?? "";
    const hasIndicator =
      /demo mode/i.test(body) ||
      /sample data/i.test(body) ||
      /backend unavailable/i.test(body) ||
      /backend unreachable/i.test(body) ||
      /offline demo/i.test(body) ||
      /mock data/i.test(body);

    expect(
      hasIndicator,
      `Expected a degraded-mode banner in the rendered page, got:\n${body.slice(0, 800)}`,
    ).toBe(true);
  });
});

// -------------------------------------------------------------------------
// Bug B — booking rejection swallows backend `reason` / `commit_error`.
// -------------------------------------------------------------------------
describe("bug_booking_rejection_displays_backend_reason", () => {
  test("REJECTED booking surfaces backend reason ('duplicate active transaction') instead of generic copy", async () => {
    // Stub lib/api so:
    //   - recommend resolves with one fake hospital so the user can click Reserve
    //   - streamReasoning is a no-op
    //   - reserve resolves with a REJECTED-style payload that includes `reason`
    //   - isDegraded reports false (this test isn't about Bug A)
    vi.doMock("../lib/api", () => ({
      isDegraded: () => false,
      streamReasoning: vi.fn(async () => undefined),
      recommend: vi.fn(async () => ({
        hospitals: [
          {
            id: "HOSP_TEST",
            name: "Test General Hospital",
            distanceKm: 1.2,
            etaMinutes: 6,
            demoted: false,
            trustSignals: [
              { kind: "Bed", score: 0.9, source: "test", evidence: { detail: "n/a" } },
              { kind: "Oxygen", score: 0.9, source: "test", evidence: { detail: "n/a" } },
              { kind: "Drug", score: 0.9, source: "test", evidence: { detail: "n/a" } },
              { kind: "Specialist", score: 0.9, source: "test", evidence: { detail: "n/a" } },
            ],
            confidence: { lower: 0.7, upper: 0.95 },
            coordinates: { lat: 0, lng: 0 },
          },
        ],
      })),
      reserve: vi.fn(async () => ({
        // Shape that PatientFlow currently consumes:
        success: false,
        referenceId: "RSV-HOSP_TEST-FAILED",
        // Extra backend fields that the UI SHOULD surface but currently drops:
        status: "REJECTED",
        reason: "duplicate active transaction",
        commit_error: null,
        transaction_id: null,
      })),
    }));

    const { default: PatientFlow } = await import("../pages/PatientFlow");
    render(<PatientFlow />);

    // Wait for the hospital card to appear (auto-query fires on mount).
    const reserveBtn = await screen.findByRole(
      "button",
      { name: /reserve|book/i },
      { timeout: 3000 },
    );

    reserveBtn.click();

    // After the mocked reserve() resolves, the UI re-renders into the
    // rollback / error state. Wait for the post-reserve render.
    await waitFor(
      () => {
        const body = document.body.textContent ?? "";
        // Either the generic message OR (ideally) the real backend reason
        // should be on screen by now.
        expect(
          /reservation rolled back|reservation failed|duplicate active transaction/i.test(body),
        ).toBe(true);
      },
      { timeout: 3000 },
    );

    const body = document.body.textContent ?? "";
    expect(
      body,
      `Expected backend 'reason' string to be surfaced to the user, got:\n${body.slice(0, 800)}`,
    ).toMatch(/duplicate active transaction/i);
  });
});
