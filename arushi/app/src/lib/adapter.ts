// Bridge between canonical backend Hospital (snake_case, flat trust) and the
// legacy UI Hospital shape (camelCase, trustSignals[]). Pure data transform —
// no network, no React, no side effects.

import type {
  CanonicalHospital,
  Hospital,
  RailwayRecommendHospital,
  TrustEvidence,
  TrustKind,
  TrustSignal,
} from "./types";

// Approximate hub for distance fallback when no user location is available.
const DEFAULT_USER_LAT = 19.076;
const DEFAULT_USER_LON = 72.8777;

// If the calibrated trust dips this far below the raw signal we mark the row
// `demoted` so the UI can surface the "models disagree" tile. Pulled out as a
// named constant because the same threshold is referenced in the backend
// trust-blender doc — keep them in lockstep.
export const MAX_FACTOR_DISAGREEMENT_THRESHOLD = 0.05;

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

// Antimeridian note: this implementation uses signed dLon, which is fine for
// any pair of points on the same side of the ±180 line — i.e. all of Mumbai's
// service area. If we ever expand to facilities crossing the antimeridian
// (Aleutians / Fiji / NZ) the dLon term needs wrap-around handling.
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

type AdaptableHospital = CanonicalHospital | RailwayRecommendHospital;

function isRailwayRecommendHospital(h: AdaptableHospital): h is RailwayRecommendHospital {
  return "hospital_id" in h;
}

function hospitalId(h: AdaptableHospital): string {
  return isRailwayRecommendHospital(h) ? String(h.hospital_id) : h.facility_id;
}

function trustScore(h: AdaptableHospital): number {
  if (isRailwayRecommendHospital(h)) {
    return Math.min(0.98, Math.max(0.35, h.specialty_match));
  }
  return h.trust_calibrated;
}

function trustSource(h: AdaptableHospital): string {
  return isRailwayRecommendHospital(h) ? "live-route-score" : h.trust_source;
}

function trustEvidence(h: AdaptableHospital): TrustEvidence {
  if (isRailwayRecommendHospital(h)) {
    return {
      summary: `Live route match ${(h.specialty_match * 100).toFixed(0)}%, estimated travel ${h.travel_min} min.`,
      method: "live-route-score",
      sourceId: String(h.hospital_id),
    };
  }
  return {
    summary: `Hybrid trust ${h.trust_calibrated.toFixed(2)} (raw ${h.trust_score.toFixed(2)}, source: ${h.trust_source}).`,
    lastUpdatedAt: undefined,
    method: h.trust_source,
    sourceId: `${h.facility_id}-${h.trust_source}`,
  };
}

function makeTrustSignals(h: AdaptableHospital): TrustSignal[] {
  const score = trustScore(h);
  const ci = isRailwayRecommendHospital(h)
    ? 0.04
    : Math.min(0.15, Math.max(0.02, h.max_factor_disagreement ?? 0.04));
  const evidence = trustEvidence(h);
  const kinds: TrustKind[] = ["Bed", "Oxygen", "Drug", "Specialist"];
  return kinds.map((kind) => ({
    kind,
    score,
    ci,
    source: trustSource(h),
    evidence,
  }));
}

export interface AdaptOptions {
  userLat?: number;
  userLon?: number;
}

export function adaptHospital(
  h: AdaptableHospital,
  opts: AdaptOptions = {},
): Hospital {
  ensureUserLocation();
  const userLat = opts.userLat ?? _cachedUserLat ?? DEFAULT_USER_LAT;
  const userLon = opts.userLon ?? _cachedUserLon ?? DEFAULT_USER_LON;

  // Guard against a backend row missing lat/lon (NaN/null/undefined) — without
  // this haversineKm returns NaN and the UI ends up rendering "NaN km / NaN min".
  // Fall back to 0/0 so the tile still renders; the demoted flag below still
  // catches genuine data-quality issues separately.
  const hasCoords = Number.isFinite(h.lat) && Number.isFinite(h.lon);
  const distanceKm = hasCoords
    ? Math.round(haversineKm(userLat, userLon, h.lat, h.lon) * 10) / 10
    : 0;
  const etaMinutes = isRailwayRecommendHospital(h)
    ? h.travel_min
    : hasCoords
      ? Math.max(5, Math.round(distanceKm * 3))
      : 0;
  const demoted = isRailwayRecommendHospital(h)
    ? h.specialty_match < 0.7
    : h.trust_source === "models-disagree" ||
      h.trust_calibrated + MAX_FACTOR_DISAGREEMENT_THRESHOLD < h.trust_score;

  return {
    id: hospitalId(h),
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
  hospitals: AdaptableHospital[],
  opts: AdaptOptions = {},
): Hospital[] {
  return hospitals.map((h) => adaptHospital(h, opts));
}
