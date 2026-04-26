// Failing regression tests for two real frontend bugs surfaced by the
// 10-agent audit. Both tests are intentionally RED until the bugs are fixed.
//
//  Bug A: ReasoningPanelSSE.tsx accumulates streamed events with no upper
//         bound (useState<StreamedEvent[]>([])) — long demo sessions blow
//         up the heap and crash the tab. Correct behaviour is a sliding
//         window of the N most-recent events.
//
//  Bug B: lib/adapter.ts hardcodes the user's "current location" to Mumbai
//         (DEFAULT_USER_LAT/LON). When the demo runs in Boston / SF /
//         Bangalore, the map snaps to Mumbai with no nearby hospitals.
//         Correct behaviour is to read from navigator.geolocation (with
//         Mumbai as a fallback) or from a configurable env/prop.

import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { act, cleanup, render } from "@testing-library/react";
import ReasoningPanelSSE from "../components/ReasoningPanelSSE";
import { adaptHospital } from "../lib/adapter";
import type { CanonicalHospital } from "../lib/types";

// ---------------------------------------------------------------------------
// Minimal EventSource fake: captures listeners so the test can dispatch
// arbitrary numbers of events synchronously. jsdom does not ship a real
// EventSource implementation we can drive directly, and we want full control
// over the message stream anyway.
// ---------------------------------------------------------------------------

type Listener = (ev: MessageEvent<string>) => void;

class FakeEventSource {
  static instances: FakeEventSource[] = [];

  url: string;
  readyState = 0;
  listeners: Record<string, Listener[]> = {};
  onerror: ((ev: Event) => void) | null = null;
  onopen: ((ev: Event) => void) | null = null;
  onmessage: ((ev: MessageEvent<string>) => void) | null = null;

  constructor(url: string) {
    this.url = url;
    FakeEventSource.instances.push(this);
  }

  addEventListener(type: string, cb: EventListener) {
    (this.listeners[type] ||= []).push(cb as unknown as Listener);
  }

  removeEventListener(type: string, cb: EventListener) {
    this.listeners[type] = (this.listeners[type] || []).filter(
      (l) => (l as unknown as EventListener) !== cb,
    );
  }

  emit(type: string, data: unknown) {
    const payload = typeof data === "string" ? data : JSON.stringify(data);
    const ev = new MessageEvent(type, { data: payload });
    for (const l of this.listeners[type] || []) l(ev);
  }

  close() {
    this.readyState = 2;
  }
}

// ===========================================================================
// Bug A — sliding-window cap on streamed SSE events
// ===========================================================================

describe("ReasoningPanelSSE", () => {
  const originalES = (globalThis as { EventSource?: unknown }).EventSource;

  beforeEach(() => {
    FakeEventSource.instances = [];
    (globalThis as { EventSource?: unknown }).EventSource =
      FakeEventSource as unknown as typeof EventSource;
  });

  afterEach(() => {
    cleanup();
    (globalThis as { EventSource?: unknown }).EventSource = originalES;
  });

  test("bug_sse_events_array_capped_to_window", async () => {
    const MAX_EVENTS = 200;
    const TOTAL_EVENTS = 500;

    const { container } = render(
      <ReasoningPanelSSE sessionId="test-session" useDemo={false} />,
    );

    // Component mounts in useEffect — wait a tick so it constructs the
    // EventSource and subscribes to listeners.
    await act(async () => {
      await Promise.resolve();
    });

    const es = FakeEventSource.instances[0];
    expect(es, "ReasoningPanelSSE should have created exactly one EventSource").toBeDefined();

    // Pump 500 stream_tick events into the panel — exactly the kind of
    // long-running noisy-LLM session that triggers the OOM in production.
    await act(async () => {
      for (let i = 0; i < TOTAL_EVENTS; i++) {
        es.emit("stream_tick", {
          agent: "stream_tick",
          token: `tok-${i}`,
          trace_id: "t",
          ts: "",
        });
      }
    });

    // Each rendered event becomes one <motion.div> with class "border-l-4".
    // Count them — the panel must cap to MAX_EVENTS via a sliding window.
    const rendered = container.querySelectorAll(".border-l-4");
    expect(
      rendered.length,
      `Reasoning panel kept ${rendered.length} events in state — should be ≤ ${MAX_EVENTS} (sliding window)`,
    ).toBeLessThanOrEqual(MAX_EVENTS);
  });
});

// ===========================================================================
// Bug B — user/map location must not be hardcoded to Mumbai
// ===========================================================================

describe("adapter user location", () => {
  // Boston, MA — judges' likely physical location.
  const BOSTON_LAT = 42.3601;
  const BOSTON_LON = -71.0589;

  // Mumbai constants currently baked into adapter.ts.
  const MUMBAI_LAT = 19.076;
  const MUMBAI_LON = 72.8777;

  // A hospital sitting right on top of Boston — distance from the *real*
  // user (also in Boston) should be ~0 km. Distance from Mumbai is ~12,000 km.
  const BOSTON_HOSPITAL: CanonicalHospital = {
    facility_id: "bos-1",
    name: "Boston General",
    city: "Boston",
    state: "MA",
    pincode: "02108",
    facility_type: "general",
    lat: BOSTON_LAT,
    lon: BOSTON_LON,
    trust_score: 0.9,
    trust_calibrated: 0.88,
    trust_source: "two-model-verified",
    max_factor_disagreement: 0.04,
  };

  beforeEach(() => {
    // Mock browser geolocation — the adapter SHOULD pick this up and use
    // Boston as the user's location. The buggy adapter ignores it and
    // falls back to the hardcoded Mumbai constants.
    const getCurrentPosition = vi.fn(
      (
        success: (pos: {
          coords: { latitude: number; longitude: number };
        }) => void,
      ) => {
        success({ coords: { latitude: BOSTON_LAT, longitude: BOSTON_LON } });
      },
    );
    Object.defineProperty(globalThis.navigator, "geolocation", {
      value: { getCurrentPosition },
      configurable: true,
    });
  });

  test("bug_map_center_not_hardcoded_to_mumbai", () => {
    // Call adaptHospital with NO explicit userLat/userLon — the adapter
    // must consult navigator.geolocation (or an env-driven default) and
    // resolve the user to Boston, not Mumbai.
    const adapted = adaptHospital(BOSTON_HOSPITAL);

    // Mumbai → Boston is roughly 12,500 km. If the adapter is still
    // anchored on Mumbai, distanceKm will be ~12,500. If it correctly
    // reads geolocation, distanceKm will be ~0.
    expect(
      adapted.distanceKm,
      `adaptHospital used hardcoded Mumbai (${MUMBAI_LAT}, ${MUMBAI_LON}) instead of browser geolocation (${BOSTON_LAT}, ${BOSTON_LON}) — distance to a Boston hospital should be ~0 km, got ${adapted.distanceKm}`,
    ).toBeLessThan(50);
  });
});
