import { motion } from "framer-motion";
import { AlertTriangle, HeartHandshake, MapPinned } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import L from "leaflet";
import { Circle, MapContainer, Marker, TileLayer, Tooltip } from "react-leaflet";
import { getNGODashboardData } from "../lib/api";
import type { NGODashboardData } from "../lib/types";

const ngoMarker = new L.DivIcon({
  className: "ngo-pin-marker",
  html: "<div style='width:12px;height:12px;border-radius:999px;background:#f43f5e;border:2px solid #4c0519;box-shadow:0 0 0 3px rgba(244,63,94,0.2);'></div>",
  iconSize: [12, 12],
  iconAnchor: [6, 6],
});

export default function NGODashboard() {
  const [data, setData] = useState<NGODashboardData | null>(null);
  const [specialty, setSpecialty] = useState<string>("All");
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      setIsLoading(true);
      setErrorMessage(null);
      try {
        const result = await getNGODashboardData();
        setData(result);
      } catch {
        setErrorMessage("Could not load NGO dashboard data.");
      } finally {
        setIsLoading(false);
      }
    };
    void load();
  }, []);

  const filteredPins = useMemo(() => {
    if (!data) return [];
    if (specialty === "All") return data.underservedPins;
    return data.underservedPins.filter((pin) => pin.specialty === specialty);
  }, [data, specialty]);

  const severityClass = (severity: "low" | "medium" | "high") => {
    if (severity === "high") return "border-rose-500/60 bg-rose-500/10 text-rose-200";
    if (severity === "medium") return "border-indigo-500/60 bg-indigo-500/10 text-indigo-200";
    return "border-emerald-500/60 bg-emerald-500/10 text-emerald-200";
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="space-y-4"
    >
      <div className="grid grid-cols-1 gap-4 xl:grid-cols-[1fr_1.1fr]">
        <div className="space-y-4">
          <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-5 shadow-premium">
            <div className="mb-3 inline-flex rounded-xl border border-emerald-500/40 bg-emerald-500/10 p-2.5 text-emerald-300">
              <HeartHandshake size={18} />
            </div>
            <h2 className="text-xl font-semibold text-slate-100">NGO Dashboard</h2>
            <p className="mt-2 text-sm text-slate-400">Track underserved geographies by specialty and identify emergency dead zones.</p>

            {errorMessage ? (
              <div className="mt-4 rounded-xl border border-rose-500/40 bg-rose-500/10 px-3 py-2 text-sm text-rose-200">
                {errorMessage}
              </div>
            ) : null}
            {isLoading ? (
              <div className="mt-4 rounded-xl border border-slate-800 bg-slate-950/70 px-3 py-2 text-sm text-slate-400">
                Loading NGO coverage signals...
              </div>
            ) : null}

            <div className="mt-4">
              <div className="mb-2 text-xs uppercase tracking-widest text-slate-400">Specialty filter</div>
              <div className="flex flex-wrap gap-2">
                {["All", ...(data?.specialties ?? [])].map((item) => (
                  <motion.button
                    whileHover={{ y: -1.5 }}
                    key={item}
                    type="button"
                    onClick={() => setSpecialty(item)}
                    className={`rounded-full border px-3 py-1.5 text-xs transition ${
                      specialty === item
                        ? "border-indigo-500/60 bg-indigo-500/15 text-indigo-200"
                        : "border-slate-700 bg-slate-950 text-slate-300 hover:border-slate-600"
                    }`}
                  >
                    {item}
                  </motion.button>
                ))}
              </div>
            </div>
          </div>

          <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-5 shadow-premium">
            <div className="mb-3 inline-flex rounded-xl border border-indigo-500/40 bg-indigo-500/10 p-2.5 text-indigo-300">
              <MapPinned size={18} />
            </div>
            <h3 className="text-base font-semibold text-slate-100">Underserved PIN cards</h3>
            <div className="mt-3 space-y-2">
              {!isLoading && filteredPins.length === 0 ? (
                <div className="rounded-xl border border-dashed border-slate-700 px-3 py-2 text-sm text-slate-400">
                  No underserved PINs for this specialty filter.
                </div>
              ) : null}
              {filteredPins.map((pin) => (
                <motion.div
                  key={pin.id}
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="rounded-xl border border-slate-800 bg-slate-950/80 p-3"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <div className="text-sm font-medium text-slate-200">PIN {pin.pin}</div>
                      <div className="mt-1 text-xs text-slate-400">
                        {pin.specialty} gap - {pin.populationGap.toLocaleString()} people uncovered
                      </div>
                    </div>
                    <span className={`rounded-full border px-2 py-1 text-[10px] font-medium uppercase ${severityClass(pin.severity)}`}>
                      {pin.severity}
                    </span>
                  </div>
                </motion.div>
              ))}
            </div>
          </div>

          <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-5 shadow-premium">
            <div className="mb-3 inline-flex rounded-xl border border-rose-500/40 bg-rose-500/10 p-2.5 text-rose-300">
              <AlertTriangle size={18} />
            </div>
            <h3 className="text-base font-semibold text-slate-100">Dead zone overlays</h3>
            <div className="mt-3 space-y-2">
              {(data?.deadZones ?? []).map((zone) => (
                <div key={zone.id} className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-3">
                  <div className="text-sm font-medium text-rose-200">{zone.label}</div>
                  <div className="mt-1 text-xs text-rose-100/80">{zone.description}</div>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-3 shadow-premium">
          <MapContainer center={[22.5, 79]} zoom={4.8} className="h-[760px] w-full rounded-xl">
            <TileLayer url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png" />
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
                  color: pin.severity === "high" ? "#fb7185" : pin.severity === "medium" ? "#818cf8" : "#34d399",
                  fillOpacity: 0.08,
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
