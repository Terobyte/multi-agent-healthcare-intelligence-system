import L from "leaflet";
import { useEffect } from "react";
import { MapContainer, Marker, TileLayer, Tooltip, useMap } from "react-leaflet";
import type { Hospital } from "../lib/types";
import { GlassCard } from "./ui";

const markerIcon = new L.DivIcon({
  className: "custom-hospital-marker",
  html: "<div style='width:14px;height:14px;border-radius:999px;background:#10b981;border:2px solid #022c22;box-shadow:0 0 0 3px rgba(16,185,129,0.25);'></div>",
  iconSize: [14, 14],
  iconAnchor: [7, 7],
});

// Auto-fit bounds whenever the hospital list changes so the map zooms into
// just the cluster of returned results instead of staying at all-India.
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
  return (
    <GlassCard className="h-[360px] overflow-hidden p-0">
      <MapContainer
        center={[20.5937, 78.9629]}
        zoom={5}
        scrollWheelZoom={false}
        className="h-full w-full"
      >
        <TileLayer url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png" />
        <FitToHospitals hospitals={hospitals} />
        {hospitals.map((hospital) => (
          <Marker key={hospital.id} position={[hospital.lat, hospital.lng]} icon={markerIcon}>
            <Tooltip direction="top" offset={[0, -8]} opacity={1} permanent={false}>
              {hospital.name}
            </Tooltip>
          </Marker>
        ))}
      </MapContainer>
    </GlassCard>
  );
}
