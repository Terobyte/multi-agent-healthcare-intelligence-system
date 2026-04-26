// Bridge between canonical backend Hospital (snake_case, flat trust) and the
// legacy UI Hospital shape (camelCase, trustSignals[]). Pure data transform —
// no network, no React, no side effects.

import type {
  CanonicalHospital,
  Hospital,
  TrustEvidence,
  TrustKind,
  TrustSignal,
} from "./types";

// Approximate hub for distance fallback when no user location is available.
const DEFAULT_USER_LAT = 19.076;
const DEFAULT_USER_LON = 72.8777;

// One-time geolocation probe — populated by navigator.geolocation success
// callback when the user grants access. Stays null on permission-deny / no-API,
// in which case adaptHospital falls back to the Mumbai default. Cached per
// session to avoid re-prompting on every adaptHospital call.
let _cachedUserLat: number | null = null;
let _cachedUserLon: number | null = null;

function ensureUserLocation(): void {
  if (_cachedUserLat !== null && _cachedUserLon !== null) return;
  if (typeof navigator === "undefined" || !navigator.geolocation) return;
  try {
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        _cachedUserLat = pos.coords.latitude;
        _cachedUserLon = pos.coords.longitude;
      },
      () => {
        /* permission denied — keep using Mumbai fallback */
      },
    );
  } catch {
    /* browser refused or no permissions API — silent fallback */
  }
}

function haversineKm(lat1: number, lon1: number, lat2: number, lon2: number): number {
  const R = 6371;
  const toRad = (deg: number) => (deg * Math.PI) / 180;
  const dLat = toRad(lat2 - lat1);
  const dLon = toRad(lon2 - lon1);
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLon / 2) ** 2;
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

function trustEvidence(h: CanonicalHospital): TrustEvidence {
  return {
    summary: `Hybrid trust ${h.trust_calibrated.toFixed(2)} (raw ${h.trust_score.toFixed(2)}, source: ${h.trust_source}).`,
    lastUpdatedAt: undefined,
    method: h.trust_source,
    sourceId: `${h.facility_id}-${h.trust_source}`,
  };
}

function makeTrustSignals(h: CanonicalHospital): TrustSignal[] {
  const score = h.trust_calibrated;
  const ci = Math.min(0.15, Math.max(0.02, h.max_factor_disagreement ?? 0.04));
  const evidence = trustEvidence(h);
  const kinds: TrustKind[] = ["Bed", "Oxygen", "Drug", "Specialist"];
  return kinds.map((kind) => ({
    kind,
    score,
    ci,
    source: h.trust_source,
    evidence,
  }));
}

export interface AdaptOptions {
  userLat?: number;
  userLon?: number;
}

export function adaptHospital(
  h: CanonicalHospital,
  opts: AdaptOptions = {},
): Hospital {
  ensureUserLocation();
  const userLat = opts.userLat ?? _cachedUserLat ?? DEFAULT_USER_LAT;
  const userLon = opts.userLon ?? _cachedUserLon ?? DEFAULT_USER_LON;
  const distanceKm = Math.round(haversineKm(userLat, userLon, h.lat, h.lon) * 10) / 10;
  const etaMinutes = Math.max(5, Math.round(distanceKm * 3));
  const demoted =
    h.trust_source === "models-disagree" || h.trust_calibrated + 0.05 < h.trust_score;

  return {
    id: h.facility_id,
    name: h.name,
    lat: h.lat,
    lng: h.lon,
    distanceKm,
    etaMinutes,
    demoted,
    trustSignals: makeTrustSignals(h),
  };
}

export function adaptHospitals(
  hospitals: CanonicalHospital[],
  opts: AdaptOptions = {},
): Hospital[] {
  return hospitals.map((h) => adaptHospital(h, opts));
}
