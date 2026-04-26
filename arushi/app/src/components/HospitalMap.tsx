import L from "leaflet";
import { useEffect, useMemo, useRef } from "react";
import { MapContainer, Marker, TileLayer, Tooltip, useMap } from "react-leaflet";
import type { Hospital } from "../lib/types";

// Availability comes from the average of all four trust signals (Bed / Oxygen
// / Drug / Specialist). 3 buckets, each with its own warm-palette dot:
//   high   sage    avg ≥ 0.85   = ready, lit pulse-eligible
//   ok     peach   avg ≥ 0.65   = workable
//   low    deep    avg < 0.65 OR demoted = degraded
type Availability = "high" | "ok" | "low";

function availabilityFor(hospital: Hospital): Availability {
  if (hospital.demoted) return "low";
  if (hospital.trustSignals.length === 0) return "low";
  const avg =
    hospital.trustSignals.reduce((sum, s) => sum + s.score, 0) /
    hospital.trustSignals.length;
  if (avg >= 0.85) return "high";
  if (avg >= 0.65) return "ok";
  return "low";
}

function makeIcon(level: Availability, index: number): L.DivIcon {
  const styles: Record<Availability, string> = {
    high:
      "background:#87A878;--cg-map-shadow-rest:0 0 0 4px rgba(135,168,120,0.26);--cg-map-shadow-peak:0 0 0 5px rgba(135,168,120,0.34),0 0 14px rgba(135,168,120,0.16);",
    ok:
      "background:#FFB088;--cg-map-shadow-rest:0 0 0 4px rgba(255,176,136,0.22);--cg-map-shadow-peak:0 0 0 5px rgba(255,176,136,0.30),0 0 14px rgba(255,176,136,0.14);",
    low:
      "background:#C2522B;--cg-map-shadow-rest:0 0 0 3px rgba(194,82,43,0.26);--cg-map-shadow-peak:0 0 0 4px rgba(194,82,43,0.34),0 0 12px rgba(194,82,43,0.13);opacity:0.85;",
  };
  const delay = ((index % 5) * -0.37).toFixed(2);
  return new L.DivIcon({
    className: "cg-hospital-marker",
    html: `<div class="cg-map-dot" style="width:12px;height:12px;border-radius:999px;animation-delay:${delay}s;${styles[level]}"></div>`,
    iconSize: [12, 12],
    iconAnchor: [6, 6],
  });
}

function FitToHospitals({ hospitals }: { hospitals: Hospital[] }) {
  const map = useMap();
  // Only fit on the FIRST non-empty hospitals load. Subsequent identity changes
  // (e.g. parent re-renders that recreate the array) must NOT fight the user's
  // pan/zoom mid-interaction. Tracking via ref so it survives re-renders.
  const didFitRef = useRef(false);
  useEffect(() => {
    if (hospitals.length === 0) return;
    if (didFitRef.current) return;
    const bounds = L.latLngBounds(hospitals.map((h) => [h.lat, h.lng]));
    // maxZoom 9 keeps Mumbai-area dense urban clusters readable instead of
    // over-zooming into a single pin when pad(0.25) collapses bounds.
    map.fitBounds(bounds.pad(0.25), { animate: true, maxZoom: 9 });
    didFitRef.current = true;
  }, [hospitals, map]);
  return null;
}

const legendItems: { level: Availability; label: string; color: string }[] = [
  { level: "high", label: "High", color: "#87A878" },
  { level: "ok", label: "OK", color: "#FFB088" },
  { level: "low", label: "Low", color: "#C2522B" },
];

export default function HospitalMap({ hospitals }: { hospitals: Hospital[] }) {
  const tagged = useMemo(
    () => hospitals.map((h) => ({ hospital: h, level: availabilityFor(h) })),
    [hospitals],
  );

  const cityLabel = hospitals[0]?.name
    ? `${hospitals.length} hospitals · availability`
    : "Awaiting query";

  return (
    <div className="relative h-full min-h-[260px] overflow-hidden rounded-cg-card border border-white/[0.05] bg-[#15151A] backdrop-blur-cg-glass">
      <MapContainer
        center={[20.5937, 78.9629]}
        zoom={5}
        scrollWheelZoom={false}
        className="h-full w-full"
        style={{ minHeight: 260 }}
        attributionControl={false}
      >
        <TileLayer
          url="https://{s}.basemaps.cartocdn.com/dark_nolabels/{z}/{x}/{y}{r}.png"
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
        />
        <FitToHospitals hospitals={hospitals} />
        {tagged.map(({ hospital, level }, index) => (
          <Marker key={hospital.id} position={[hospital.lat, hospital.lng]} icon={makeIcon(level, index)}>
            <Tooltip direction="top" offset={[0, -8]} opacity={1} permanent={false}>
              {hospital.name} · availability {level}
            </Tooltip>
          </Marker>
        ))}
      </MapContainer>
      <div className="pointer-events-none absolute left-14 top-4 cg-overline-rule text-[10px] font-semibold uppercase tracking-cg-overline text-cg-mist1">
        {cityLabel}
      </div>
      {hospitals.length > 0 ? (
        <div className="pointer-events-none absolute bottom-3 left-3 flex items-center gap-2 rounded-full border border-white/[0.08] bg-[rgba(20,20,21,0.85)] px-2.5 py-1 text-[10px] text-cg-mist1 backdrop-blur-cg-glass">
          {legendItems.map((item) => (
            <span key={item.level} className="inline-flex items-center gap-1">
              <span
                className="h-2 w-2 rounded-full"
                style={{ background: item.color }}
              />
              {item.label}
            </span>
          ))}
        </div>
      ) : null}
    </div>
  );
}
