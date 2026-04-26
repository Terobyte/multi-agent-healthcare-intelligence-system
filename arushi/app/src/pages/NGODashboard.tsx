import { motion } from "framer-motion";
import { AlertTriangle, HeartHandshake, MapPinned } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import L from "leaflet";
import { Circle, MapContainer, Marker, TileLayer, Tooltip, useMap } from "react-leaflet";
import { getNGODashboardData } from "../lib/api";
import type { NGODashboardData, NGOPin } from "../lib/types";

const ngoMarker = new L.DivIcon({
  className: "ngo-pin-marker",
  html: "<div style='width:12px;height:12px;border-radius:999px;background:#FFB088;border:2px solid #2A1709;box-shadow:0 0 0 3px rgba(255,176,136,0.25);'></div>",
  iconSize: [12, 12],
  iconAnchor: [6, 6],
});

// Fits the map viewport to the visible pins on the FIRST non-empty load only.
// We deliberately do NOT re-fit on subsequent filter changes — the user has
// likely panned/zoomed by then and re-fitting would yank the camera out from
// under them. The ref-guard makes the fit idempotent for the lifetime of the
// component instance.
function FitToHospitals({ pins }: { pins: NGOPin[] }) {
  const map = useMap();
  const hasFitRef = useRef(false);

  useEffect(() => {
    if (hasFitRef.current) return;
    if (pins.length === 0) return;
    const bounds = L.latLngBounds(pins.map((pin) => [pin.lat, pin.lng] as [number, number]));
    if (!bounds.isValid()) return;
    map.fitBounds(bounds, { padding: [40, 40], maxZoom: 7 });
    hasFitRef.current = true;
  }, [map, pins]);

  return null;
}

export default function NGODashboard() {
  const [data, setData] = useState<NGODashboardData | null>(null);
  const [specialty, setSpecialty] = useState<string>("All");
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    const load = async () => {
      setIsLoading(true);
      setErrorMessage(null);
      try {
        const result = await getNGODashboardData();
        if (!active) return;
        setData(result);
      } catch {
        if (!active) return;
        setErrorMessage("Could not load NGO dashboard data.");
      } finally {
        if (active) setIsLoading(false);
      }
    };
    void load();
    return () => {
      active = false;
    };
  }, []);

  const filteredPins = useMemo(() => {
    if (!data) return [];
    if (specialty === "All") return data.underservedPins;
    return data.underservedPins.filter((pin) => pin.specialty === specialty);
  }, [data, specialty]);

  // Dedupe explicitly: backends sometimes return "All" inside specialties[]
  // (especially when adapters get sloppy), which would otherwise produce two
  // identical pills with React key collisions.
  const specialtyOptions = useMemo(
    () => ["All", ...(data?.specialties ?? []).filter((s) => s !== "All")],
    [data?.specialties],
  );

  const severityClass = (severity: "low" | "medium" | "high") => {
    if (severity === "high")
      return "border-[rgba(194,82,43,0.40)] bg-[rgba(194,82,43,0.20)] text-cg-peach";
    if (severity === "medium")
      return "border-[rgba(255,176,136,0.30)] bg-[rgba(255,176,136,0.15)] text-cg-peach";
    return "border-[rgba(135,168,120,0.30)] bg-[rgba(135,168,120,0.15)] text-cg-sage";
  };

  const severityCircleColor = (severity: "low" | "medium" | "high") => {
    if (severity === "high") return "#C2522B";
    if (severity === "medium") return "#FFB088";
    return "#87A878";
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="space-y-4"
    >
      <div className="grid grid-cols-1 gap-4 xl:grid-cols-[1fr_1.1fr]">
        <div className="space-y-4">
          <div className="rounded-cg-card border border-white/[0.05] bg-[rgba(35,35,36,0.85)] p-5 backdrop-blur-cg-glass">
            <div className="mb-3 inline-flex rounded-xl border border-[rgba(135,168,120,0.30)] bg-[rgba(135,168,120,0.15)] p-2.5 text-cg-sage">
              <HeartHandshake size={18} />
            </div>
            <h2 className="text-xl font-semibold tracking-cg-tight text-cg-ivory">NGO Dashboard</h2>
            <p className="mt-2 text-sm text-cg-mist2">
              Track underserved geographies by specialty and identify emergency dead zones.
            </p>

            {errorMessage ? (
              <div className="mt-4 rounded-cg-tile border border-[rgba(194,82,43,0.40)] bg-[rgba(194,82,43,0.15)] px-3 py-2 text-sm text-cg-peach">
                {errorMessage}
              </div>
            ) : null}
            {isLoading ? (
              <div className="mt-4 rounded-cg-tile border border-white/[0.05] bg-[rgba(20,20,21,0.7)] px-3 py-2 text-sm text-cg-mist2">
                Loading NGO coverage signals...
              </div>
            ) : null}

            <div className="mt-4">
              <div className="mb-2 text-xs uppercase tracking-cg-overline text-cg-mist4">Specialty filter</div>
              <div className="flex flex-wrap gap-2">
                {isLoading && !data ? (
                  <>
                    <div className="h-[30px] w-[52px] animate-pulse rounded-full border border-white/[0.06] bg-[rgba(40,40,42,0.7)]" />
                    <div className="h-[30px] w-[78px] animate-pulse rounded-full border border-white/[0.06] bg-[rgba(40,40,42,0.7)]" />
                    <div className="h-[30px] w-[64px] animate-pulse rounded-full border border-white/[0.06] bg-[rgba(40,40,42,0.7)]" />
                    <div className="h-[30px] w-[88px] animate-pulse rounded-full border border-white/[0.06] bg-[rgba(40,40,42,0.7)]" />
                  </>
                ) : (
                  specialtyOptions.map((item) => (
                    <motion.button
                      whileHover={{ y: -1.5 }}
                      key={item}
                      type="button"
                      onClick={() => setSpecialty(item)}
                      className={`rounded-full border px-3 py-1.5 text-xs font-semibold transition ${
                        specialty === item
                          ? "border-[rgba(255,176,136,0.30)] bg-[rgba(255,176,136,0.15)] text-cg-peach"
                          : "border-white/[0.08] bg-[rgba(20,20,21,0.6)] text-cg-mist2 hover:border-white/[0.16]"
                      }`}
                    >
                      {item}
                    </motion.button>
                  ))
                )}
              </div>
            </div>
          </div>

          <div className="rounded-cg-card border border-white/[0.05] bg-[rgba(35,35,36,0.85)] p-5 backdrop-blur-cg-glass">
            <div className="mb-3 inline-flex rounded-xl border border-[rgba(255,176,136,0.30)] bg-[rgba(255,176,136,0.15)] p-2.5 text-cg-peach">
              <MapPinned size={18} />
            </div>
            <h3 className="text-base font-semibold tracking-[-0.01em] text-cg-ivory">Underserved PIN cards</h3>
            <div className="mt-3 space-y-2">
              {!isLoading && filteredPins.length === 0 ? (
                <div className="rounded-cg-tile border border-dashed border-white/[0.10] px-3 py-2 text-sm text-cg-mist3">
                  No underserved PINs for this specialty filter.
                </div>
              ) : null}
              {filteredPins.map((pin) => (
                <motion.div
                  key={pin.id}
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="rounded-cg-tile border border-white/[0.05] bg-[rgba(20,20,21,0.7)] p-3"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <div className="text-sm font-medium text-cg-ivory">PIN {pin.pin}</div>
                      <div className="mt-1 text-xs text-cg-mist2">
                        {pin.specialty} gap - {pin.populationGap.toLocaleString()} people uncovered
                      </div>
                    </div>
                    <span className={`rounded-full border px-2 py-1 text-[10px] font-semibold uppercase tracking-cg-overline ${severityClass(pin.severity)}`}>
                      {pin.severity}
                    </span>
                  </div>
                </motion.div>
              ))}
            </div>
          </div>

          <div className="rounded-cg-card border border-white/[0.05] bg-[rgba(35,35,36,0.85)] p-5 backdrop-blur-cg-glass">
            <div className="mb-3 inline-flex rounded-xl border border-[rgba(194,82,43,0.40)] bg-[rgba(194,82,43,0.15)] p-2.5 text-cg-peach">
              <AlertTriangle size={18} />
            </div>
            <h3 className="text-base font-semibold tracking-[-0.01em] text-cg-ivory">Dead zone overlays</h3>
            <div className="mt-3 space-y-2">
              {(data?.deadZones ?? []).map((zone) => (
                <div
                  key={zone.id}
                  className="rounded-cg-tile border border-[rgba(194,82,43,0.30)] bg-[rgba(194,82,43,0.10)] p-3"
                >
                  <div className="text-sm font-semibold text-cg-peach">{zone.label}</div>
                  <div className="mt-1 text-xs text-cg-peach/80">{zone.description}</div>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="rounded-cg-card border border-white/[0.05] bg-[rgba(35,35,36,0.85)] p-3 backdrop-blur-cg-glass">
          <MapContainer
            center={[22.5, 79]}
            zoom={5}
            scrollWheelZoom={false}
            className="h-[760px] w-full rounded-xl"
            attributionControl={false}
          >
            <TileLayer
              url="https://{s}.basemaps.cartocdn.com/dark_nolabels/{z}/{x}/{y}{r}.png"
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
            />
            <FitToHospitals pins={filteredPins} />
            {filteredPins.map((pin) => (
              <Marker key={pin.id} position={[pin.lat, pin.lng]} icon={ngoMarker}>
                <Tooltip>
                  PIN {pin.pin} - {pin.specialty}
                </Tooltip>
              </Marker>
            ))}
            {filteredPins.map((pin) => (
              <Circle
                key={`${pin.id}-radius`}
                center={[pin.lat, pin.lng]}
                radius={pin.severity === "high" ? 52000 : pin.severity === "medium" ? 38000 : 25000}
                pathOptions={{
                  color: severityCircleColor(pin.severity),
                  fillOpacity: 0.10,
                  weight: 1,
                }}
              />
            ))}
          </MapContainer>
        </div>
      </div>
    </motion.div>
  );
}
