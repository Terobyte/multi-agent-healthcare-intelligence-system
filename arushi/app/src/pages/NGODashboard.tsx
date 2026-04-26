import { motion } from "framer-motion";
import { AlertTriangle, HeartHandshake, MapPinned } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import L from "leaflet";
import { Circle, MapContainer, Marker, TileLayer, Tooltip, useMap } from "react-leaflet";
import { getNGODashboardData } from "../lib/api";
import type { NGODashboardData, NGOPin } from "../lib/types";
import GeniePanel from "../components/GeniePanel";

// Specialty → warm-palette dot color. Matched pins (or all pins on "All")
// render in their full specialty hue; unmatched pins (when a filter is active)
// fade to charcoal with reduced opacity, so the match relationship reads at
// a glance without yanking pins off the map.
const specialtyDotColor: Record<string, string> = {
  Trauma: "#FFB088",
  Cardiac: "#E87B43",
  Neuro: "#C8E4D0",
  Pediatric: "#87A878",
};
const fallbackDotColor = "#9A9690";

function buildPinIcon(specialty: string, matched: boolean, index: number): L.DivIcon {
  const color = specialtyDotColor[specialty] ?? fallbackDotColor;
  const delay = ((index % 5) * -0.37).toFixed(2);
  if (matched) {
    return new L.DivIcon({
      className: "ngo-pin-marker",
      html: `<div class="cg-ngo-pin-shell"><div class="cg-map-dot" style="width:14px;height:14px;border-radius:999px;background:${color};border:2px solid #2A1709;--cg-map-shadow-rest:0 0 0 4px ${color}4D;--cg-map-shadow-peak:0 0 0 5px ${color}66,0 0 14px ${color}24;animation-delay:${delay}s;"></div></div>`,
      iconSize: [18, 18],
      iconAnchor: [9, 9],
    });
  }
  return new L.DivIcon({
    className: "ngo-pin-marker ngo-pin-faded",
    html: `<div class="cg-ngo-pin-shell"><div style="width:9px;height:9px;border-radius:999px;background:#5A5550;border:1px solid #2A1709;opacity:0.55;"></div></div>`,
    iconSize: [18, 18],
    iconAnchor: [9, 9],
  });
}

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

  // Five tones drawn from the warm-lantern peach/sage scale — keeps brand
  // discipline (no new hues) while still letting each specialty read by color.
  // Active = tinted fill + matching text/border. Inactive = neutral chrome
  // with the specialty colour just on the text so the chip still hints
  // identity at a glance.
  const specialtyTone: Record<string, { active: string; inactive: string }> = {
    All: {
      active: "border-white/[0.20] bg-white/[0.08] text-cg-ivory",
      inactive: "border-white/[0.08] bg-[rgba(20,20,21,0.6)] text-cg-mist1 hover:border-white/[0.16]",
    },
    Trauma: {
      active: "border-[rgba(255,176,136,0.45)] bg-[rgba(255,176,136,0.18)] text-cg-peach",
      inactive: "border-white/[0.08] bg-[rgba(20,20,21,0.6)] text-[#FFB088]/75 hover:border-[rgba(255,176,136,0.30)]",
    },
    Cardiac: {
      active: "border-[rgba(232,123,67,0.50)] bg-[rgba(232,123,67,0.20)] text-[#FFB088]",
      inactive: "border-white/[0.08] bg-[rgba(20,20,21,0.6)] text-[#E87B43]/85 hover:border-[rgba(232,123,67,0.35)]",
    },
    Neuro: {
      active: "border-[rgba(200,228,208,0.45)] bg-[rgba(200,228,208,0.18)] text-cg-sage",
      inactive: "border-white/[0.08] bg-[rgba(20,20,21,0.6)] text-[#C8E4D0]/75 hover:border-[rgba(200,228,208,0.30)]",
    },
    Pediatric: {
      active: "border-[rgba(135,168,120,0.50)] bg-[rgba(135,168,120,0.20)] text-[#C8E4D0]",
      inactive: "border-white/[0.08] bg-[rgba(20,20,21,0.6)] text-[#87A878] hover:border-[rgba(135,168,120,0.35)]",
    },
  };
  const fallbackTone = specialtyTone.All;

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
                  specialtyOptions.map((item) => {
                    const tone = specialtyTone[item] ?? fallbackTone;
                    const active = specialty === item;
                    return (
                      <motion.button
                        whileHover={{ y: -1.5 }}
                        key={item}
                        type="button"
                        onClick={() => setSpecialty(item)}
                        className={`rounded-full border px-3 py-1.5 text-xs font-semibold transition ${
                          active ? tone.active : tone.inactive
                        }`}
                      >
                        {item}
                      </motion.button>
                    );
                  })
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
          <div className="relative min-h-[760px] overflow-hidden rounded-xl bg-[rgba(20,20,21,0.92)]">
            <MapContainer
              center={[22.5, 79]}
              zoom={5}
              scrollWheelZoom={false}
              className="h-[760px] w-full"
              attributionControl={false}
            >
              <TileLayer
                url="https://{s}.basemaps.cartocdn.com/dark_nolabels/{z}/{x}/{y}{r}.png"
                attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
              />
              <FitToHospitals pins={data?.underservedPins ?? []} />
              {(data?.underservedPins ?? []).map((pin, index) => {
                const matched = specialty === "All" || pin.specialty === specialty;
                return (
                  <Marker
                    key={pin.id}
                    position={[pin.lat, pin.lng]}
                    icon={buildPinIcon(pin.specialty, matched, index)}
                    // Faded pins shouldn't steal clicks while a filter is active —
                    // user is explicitly hunting matched pins; greyed dots are
                    // context, not interactive targets.
                    interactive={matched}
                  >
                    <Tooltip>
                      PIN {pin.pin} · {pin.specialty}
                    </Tooltip>
                  </Marker>
                );
              })}
              {/* Severity radius rings — only on matched pins so the fade reads
                  cleanly. The ring colour stays severity-driven so high-severity
                  gaps still pop visually inside the matched set. */}
              {(data?.underservedPins ?? [])
                .filter((pin) => specialty === "All" || pin.specialty === specialty)
                .map((pin) => (
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
            {isLoading || (!data && errorMessage) ? (
              <div className="pointer-events-none absolute inset-0 flex items-center justify-center bg-[rgba(20,20,21,0.72)] px-6 text-center text-sm text-cg-mist2">
                {isLoading ? "Loading NGO coverage map..." : "NGO data unavailable. Check the panel on the left."}
              </div>
            ) : null}
          </div>
        </div>
      </div>

      <GeniePanel />
    </motion.div>
  );
}
