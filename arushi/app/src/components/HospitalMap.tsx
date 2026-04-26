import L from "leaflet";
import { useEffect, useMemo } from "react";
import { MapContainer, Marker, TileLayer, Tooltip, useMap } from "react-leaflet";
import type { Hospital } from "../lib/types";

type Tier = "best" | "backup" | "faded";

function tierFor(hospital: Hospital, isFirstNonDemoted: boolean): Tier {
  if (hospital.demoted) return "faded";
  if (isFirstNonDemoted) return "best";
  return "backup";
}

function makeIcon(tier: Tier): L.DivIcon {
  const styles: Record<Tier, string> = {
    best: "background:#87A878;box-shadow:0 0 0 4px rgba(135,168,120,0.25);",
    backup: "background:#FFB088;box-shadow:0 0 0 4px rgba(255,176,136,0.25);",
    faded: "background:#5A5550;box-shadow:0 0 0 3px rgba(255,255,255,0.04);opacity:0.7;",
  };
  return new L.DivIcon({
    className: "cg-hospital-marker",
    html: `<div style="width:12px;height:12px;border-radius:999px;${styles[tier]}"></div>`,
    iconSize: [12, 12],
    iconAnchor: [6, 6],
  });
}

function FitToHospitals({ hospitals }: { hospitals: Hospital[] }) {
  const map = useMap();
  useEffect(() => {
    if (hospitals.length === 0) return;
    const bounds = L.latLngBounds(hospitals.map((h) => [h.lat, h.lng]));
    map.fitBounds(bounds.pad(0.25), { animate: true, maxZoom: 11 });
  }, [hospitals, map]);
  return null;
}

export default function HospitalMap({ hospitals }: { hospitals: Hospital[] }) {
  const ranked = useMemo(() => {
    let bestUsed = false;
    return hospitals.map((h) => {
      const isFirst = !h.demoted && !bestUsed;
      if (isFirst) bestUsed = true;
      return { hospital: h, tier: tierFor(h, isFirst) };
    });
  }, [hospitals]);

  const cityLabel =
    hospitals[0]?.name ? `${hospitals.length} hospitals` : "Awaiting query";

  return (
    <div className="relative h-full min-h-[260px] overflow-hidden rounded-cg-card border border-white/[0.05] bg-[#15151A] backdrop-blur-cg-glass">
      <MapContainer
        center={[20.5937, 78.9629]}
        zoom={5}
        scrollWheelZoom={false}
        className="h-full w-full"
        style={{ minHeight: 260 }}
        zoomControl={false}
      >
        <TileLayer url="https://{s}.basemaps.cartocdn.com/dark_nolabels/{z}/{x}/{y}{r}.png" />
        <FitToHospitals hospitals={hospitals} />
        {ranked.map(({ hospital, tier }) => (
          <Marker key={hospital.id} position={[hospital.lat, hospital.lng]} icon={makeIcon(tier)}>
            <Tooltip direction="top" offset={[0, -8]} opacity={1} permanent={false}>
              {hospital.name}
            </Tooltip>
          </Marker>
        ))}
      </MapContainer>
      <div className="pointer-events-none absolute left-4 top-4 text-[10px] font-semibold uppercase tracking-cg-overline text-cg-mist1">
        {cityLabel}
      </div>
    </div>
  );
}
