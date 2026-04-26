import { motion } from "framer-motion";
import { useCallback, useEffect, useRef, useState } from "react";
import AtomicBookingTiles, { type BookingState } from "../components/AtomicBookingTiles";
import ChatInput from "../components/ChatInput";
import HospitalCard from "../components/HospitalCard";
import HospitalMap from "../components/HospitalMap";
import ReasoningPanel, { type RenderedReasoningRow } from "../components/ReasoningPanel";
import SourceModal from "../components/SourceModal";
import { isDegraded, recommend, reserve, streamReasoning } from "../lib/api";
import type { Hospital, TrustEvidence } from "../lib/types";

const agentById: Record<string, RenderedReasoningRow["agent"]> = {
  route_1: "Routing Agent",
  risk_1: "Risk Agent",
  verify_1: "Verification Agent",
};

// Module-level (survives unmount/remount across tab switches in App.tsx, where
// AnimatePresence + key={activeTab} unmounts the page). useRef would reset.
let _autoQuerySent = false;

const navItems = [
  { label: "Find care", active: true, badge: "Now" },
  { label: "My visits", active: false },
  { label: "Records", active: false },
  { label: "Messages", active: false },
  { label: "Settings", active: false },
];

export default function PatientFlow() {
  const [hospitals, setHospitals] = useState<Hospital[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [reservingId, setReservingId] = useState<string | null>(null);
  const [rows, setRows] = useState<RenderedReasoningRow[]>([]);
  const [bookingState, setBookingState] = useState<BookingState>("idle");
  const [sourceModal, setSourceModal] = useState<{
    open: boolean;
    title: string;
    evidence: string;
    details?: TrustEvidence;
  }>({
    open: false,
    title: "",
    evidence: "",
  });
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  // Initialize from isDegraded() so the banner appears synchronously when the
  // app is built without VITE_PUBLIC_URL — otherwise users see fake data with
  // no warning until the first recommend() call resolves.
  const [degraded, setDegraded] = useState<boolean>(() => isDegraded());
  // Block setState after unmount + tag every async run with a request id so a
  // stale stream from a prior recommend() can be ignored when the user submits
  // a new query mid-flight (race-condition fix from audit).
  const isMountedRef = useRef(true);
  const hasInitializedRef = useRef(false);
  const bookingTimersRef = useRef<number[]>([]);
  const requestSeqRef = useRef(0);

  useEffect(() => {
    isMountedRef.current = true;
    return () => {
      isMountedRef.current = false;
      bookingTimersRef.current.forEach((id) => window.clearTimeout(id));
      bookingTimersRef.current = [];
    };
  }, []);

  const runRecommendation = useCallback(async (query: string) => {
    if (!isMountedRef.current) return;
    const myReq = ++requestSeqRef.current;
    setIsLoading(true);
    setErrorMessage(null);
    setRows([]);
    try {
      const response = await recommend({ query });
      if (!isMountedRef.current || myReq !== requestSeqRef.current) return;
      setHospitals(response.hospitals);
      setDegraded(isDegraded());
      await streamReasoning((msgId, token) => {
        if (!isMountedRef.current || myReq !== requestSeqRef.current) return;
        setRows((prev) => {
          const existing = prev.find((x) => x.id === msgId);
          if (!existing) {
            return [
              ...prev,
              { id: msgId, agent: agentById[msgId] ?? "Routing Agent", text: token },
            ];
          }
          return prev.map((x) => (x.id === msgId ? { ...x, text: `${x.text} ${token}` } : x));
        });
      });
    } catch {
      if (!isMountedRef.current || myReq !== requestSeqRef.current) return;
      // Allow retry — a failed first auto-fetch shouldn't lock out the page.
      _autoQuerySent = false;
      setErrorMessage("Could not fetch recommendations. Try again in a few seconds.");
    } finally {
      if (isMountedRef.current && myReq === requestSeqRef.current) setIsLoading(false);
    }
  }, []);

  const reserveHospital = useCallback(async (hospitalId: string) => {
    bookingTimersRef.current.forEach((id) => window.clearTimeout(id));
    bookingTimersRef.current = [];
    setReservingId(hospitalId);
    setBookingState("reserving");
    setErrorMessage(null);
    try {
      const result = await reserve({ hospitalId });
      if (!isMountedRef.current) return;
      if (!result.success) {
        // Backend returned ROLLED_BACK or REJECTED — surface the real reason
        // (e.g. "duplicate active transaction", "ambulance unavailable") so
        // demo viewers see WHY the saga rolled back, not a generic string.
        setBookingState("rollback");
        const detail = result.reason || result.commit_error || null;
        setErrorMessage(
          detail
            ? `Reservation rolled back: ${detail}.`
            : "Reservation rolled back. Try a different hospital.",
        );
        bookingTimersRef.current.push(
          window.setTimeout(() => isMountedRef.current && setBookingState("idle"), 1300),
        );
      } else {
        setBookingState("success");
        bookingTimersRef.current.push(
          window.setTimeout(() => isMountedRef.current && setBookingState("rollback"), 1800),
          window.setTimeout(() => isMountedRef.current && setBookingState("idle"), 2800),
        );
      }
    } catch {
      if (!isMountedRef.current) return;
      setBookingState("rollback");
      setErrorMessage("Reservation failed. Please retry.");
      bookingTimersRef.current.push(
        window.setTimeout(() => isMountedRef.current && setBookingState("idle"), 1300),
      );
    } finally {
      if (isMountedRef.current) setReservingId(null);
    }
  }, []);

  const onTrustChipClick = useCallback(
    ({
      hospitalName,
      trustKind,
      source,
      evidence,
    }: {
      hospitalName: string;
      trustKind: string;
      source: string;
      evidence?: TrustEvidence;
    }) => {
      setSourceModal({
        open: true,
        title: `${hospitalName} - ${trustKind}`,
        evidence: source,
        details: evidence,
      });
    },
    [],
  );

  useEffect(() => {
    if (_autoQuerySent || hasInitializedRef.current) return;
    hasInitializedRef.current = true;
    _autoQuerySent = true;
    void runRecommendation("Auto triage critical care options nearby.");
  }, [runRecommendation]);

  const lit = hospitals[0];
  const backups = hospitals.slice(1, 3);
  const subline = hospitals.length
    ? `${hospitals.length} hospitals near you · live availability checked seconds ago`
    : isLoading
      ? "Triaging your symptoms…"
      : "Awaiting your symptoms.";

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="relative overflow-hidden rounded-cg-stage bg-cg-stage px-8 pb-10 pt-9"
    >
      {/* Lantern blooms — peach top-right, sage bottom-left. */}
      <div className="pointer-events-none absolute -right-16 -top-20 h-72 w-72 rounded-full bg-cg-bloom-peach opacity-55 blur-[70px]" />
      <div className="pointer-events-none absolute -bottom-24 -left-16 h-56 w-56 rounded-full bg-cg-bloom-sage opacity-50 blur-[70px]" />

      <div className="relative z-[2] grid gap-7 lg:grid-cols-[240px_1fr]">
        {/* ── Sidebar ─────────────────────────────────────── */}
        <aside className="flex min-h-[500px] flex-col gap-1.5 rounded-[22px] border border-white/[0.06] bg-[rgba(20,20,21,0.7)] px-4 py-6 backdrop-blur-cg-sidebar">
          <div className="mb-5 flex items-center gap-2.5 px-2.5">
            <div className="h-[26px] w-[26px] rounded-lg bg-cg-grad-logo-peach" />
            <span className="text-[15px] font-semibold tracking-cg-tight text-cg-ivory">
              CareGuide
            </span>
          </div>
          {navItems.map((item) => (
            <div
              key={item.label}
              className={`flex cursor-pointer items-center gap-3 rounded-xl px-3.5 py-2.5 text-[13px] transition ${
                item.active
                  ? "bg-[rgba(255,176,136,0.12)] text-cg-peach"
                  : "text-cg-mist2 hover:bg-white/[0.04] hover:text-cg-mist5"
              }`}
            >
              <span
                className={`h-1.5 w-1.5 rounded-full ${item.active ? "bg-cg-peach" : "bg-current opacity-50"}`}
              />
              {item.label}
              {item.badge ? (
                <span className="ml-auto rounded-full bg-[rgba(255,176,136,0.2)] px-2 py-0.5 text-[10px] font-semibold text-cg-peach">
                  {item.badge}
                </span>
              ) : null}
            </div>
          ))}
          <div className="mt-auto flex items-center gap-2.5 rounded-2xl bg-[rgba(40,40,42,0.7)] px-3 py-2.5 text-[12px] text-cg-mist5">
            <div className="h-7 w-7 flex-shrink-0 rounded-full bg-cg-grad-logo-sage" />
            <div className="leading-tight">
              Priya S.
              <span className="block text-[10px] text-cg-mist3">Patient</span>
            </div>
          </div>
        </aside>

        {/* ── Main ─────────────────────────────────────── */}
        <main className="flex min-w-0 flex-col gap-4">
          <div className="flex flex-wrap items-end justify-between gap-3">
            <div>
              <h1 className="text-[28px] font-semibold tracking-cg-tight text-cg-ivory">
                Where to go now
              </h1>
              <p className="mt-1 text-[13px] text-cg-mist2">{subline}</p>
            </div>
            <div className="min-w-[260px] rounded-full border border-white/[0.05] bg-[rgba(40,40,42,0.7)] px-5 py-2.5 text-[13px] text-cg-mist4">
              Search by symptom or care type…
            </div>
          </div>

          <ChatInput onSend={runRecommendation} loading={isLoading} />

          {degraded ? (
            <div className="rounded-cg-tile border border-[rgba(255,176,136,0.30)] bg-[rgba(255,176,136,0.10)] px-4 py-2 text-[12px] text-cg-peach">
              Backend unreachable — showing offline demo data.
            </div>
          ) : null}
          {errorMessage ? (
            <div className="rounded-cg-tile border border-[rgba(194,82,43,0.40)] bg-[rgba(194,82,43,0.15)] px-4 py-2 text-[13px] text-cg-peach">
              {errorMessage}
            </div>
          ) : null}

          {/* 3-card hero row */}
          {hospitals.length > 0 ? (
            <div className="grid gap-3.5 lg:grid-cols-[1.5fr_1fr_1fr]">
              {lit ? (
                <HospitalCard
                  hospital={lit}
                  variant="lit"
                  overline="Best match"
                  onReserve={reserveHospital}
                  onTrustChipClick={onTrustChipClick}
                  reserving={reservingId === lit.id}
                />
              ) : null}
              {backups.map((hospital) => (
                <HospitalCard
                  key={hospital.id}
                  hospital={hospital}
                  variant="glass"
                  overline="Backup"
                  onReserve={reserveHospital}
                  onTrustChipClick={onTrustChipClick}
                  reserving={reservingId === hospital.id}
                />
              ))}
            </div>
          ) : !isLoading ? (
            <div className="rounded-cg-card border border-dashed border-white/[0.10] px-5 py-6 text-[13px] text-cg-mist3">
              No hospitals matched this query. Try broader terms.
            </div>
          ) : (
            <div className="grid gap-3.5 lg:grid-cols-[1.5fr_1fr_1fr]">
              {[1, 2, 3].map((i) => (
                <div
                  key={i}
                  className="h-[240px] animate-pulse rounded-cg-card border border-white/[0.05] bg-[rgba(35,35,36,0.85)]"
                />
              ))}
            </div>
          )}

          {/* map + atomic */}
          <div className="grid gap-3.5 lg:grid-cols-2">
            <HospitalMap hospitals={hospitals} />
            <AtomicBookingTiles state={bookingState} />
          </div>

          {/* reasoning */}
          <ReasoningPanel rows={rows} loading={isLoading} />
        </main>
      </div>

      <SourceModal
        open={sourceModal.open}
        title={sourceModal.title}
        evidence={sourceModal.evidence}
        details={sourceModal.details}
        onClose={() => setSourceModal((prev) => ({ ...prev, open: false }))}
      />
    </motion.div>
  );
}
