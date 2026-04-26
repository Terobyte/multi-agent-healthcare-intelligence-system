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

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-4">
      <div className="grid grid-cols-1 gap-4 xl:grid-cols-[1.1fr_0.9fr]">
        <div className="space-y-4">
          <ChatInput onSend={runRecommendation} loading={isLoading} />
          {degraded ? (
            <div className="rounded-xl border border-amber-500/40 bg-amber-500/10 px-4 py-2 text-xs text-amber-200">
              Backend unreachable — showing offline demo data.
            </div>
          ) : null}
          {errorMessage ? (
            <div className="rounded-xl border border-rose-500/40 bg-rose-500/10 px-4 py-2 text-sm text-rose-200">
              {errorMessage}
            </div>
          ) : null}
          {!isLoading && !errorMessage && hospitals.length === 0 ? (
            <div className="rounded-xl border border-dashed border-slate-700 px-4 py-3 text-sm text-slate-400">
              No hospitals matched this query. Try broader terms.
            </div>
          ) : null}
          <div className="space-y-3">
            {hospitals.map((hospital) => (
              <HospitalCard
                key={hospital.id}
                hospital={hospital}
                onReserve={reserveHospital}
                onTrustChipClick={onTrustChipClick}
                reserving={reservingId === hospital.id}
              />
            ))}
          </div>
        </div>
        <div className="space-y-4">
          <HospitalMap hospitals={hospitals} />
          <AtomicBookingTiles state={bookingState} />
          <ReasoningPanel rows={rows} loading={isLoading} />
        </div>
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
