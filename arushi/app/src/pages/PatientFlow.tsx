import { motion } from "framer-motion";
import { useEffect, useMemo, useState } from "react";
import AtomicBookingTiles, { type BookingState } from "../components/AtomicBookingTiles";
import ChatInput from "../components/ChatInput";
import HospitalCard from "../components/HospitalCard";
import HospitalMap from "../components/HospitalMap";
import ReasoningPanel, { type RenderedReasoningRow } from "../components/ReasoningPanel";
import SourceModal from "../components/SourceModal";
import { recommend, reserve, streamReasoning } from "../lib/api";
import type { Hospital, TrustEvidence } from "../lib/types";

const agentById: Record<string, RenderedReasoningRow["agent"]> = {
  route_1: "Routing Agent",
  risk_1: "Risk Agent",
  verify_1: "Verification Agent",
};

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

  const rowsById = useMemo(() => new Map(rows.map((row) => [row.id, row])), [rows]);

  const runRecommendation = async (query: string) => {
    setIsLoading(true);
    setErrorMessage(null);
    setRows([]);
    try {
      const response = await recommend({ query });
      setHospitals(response.hospitals);
      await streamReasoning((msgId, token) => {
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
      setHospitals([]);
      setRows([]);
      setErrorMessage("Could not fetch recommendations. Try again in a few seconds.");
    } finally {
      setIsLoading(false);
    }
  };

  const reserveHospital = async (hospitalId: string) => {
    setReservingId(hospitalId);
    setBookingState("reserving");
    setErrorMessage(null);
    try {
      await reserve({ hospitalId });
      setBookingState("success");
      window.setTimeout(() => setBookingState("rollback"), 1800);
      window.setTimeout(() => setBookingState("idle"), 2800);
    } catch {
      setBookingState("rollback");
      setErrorMessage("Reservation failed. Please retry.");
      window.setTimeout(() => setBookingState("idle"), 1300);
    } finally {
      setReservingId(null);
    }
  };

  useEffect(() => {
    if (hospitals.length === 0 && rowsById.size === 0) {
      void runRecommendation("Auto triage critical care options nearby.");
    }
  }, [hospitals.length, rowsById.size]);

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-4">
      <div className="grid grid-cols-1 gap-4 xl:grid-cols-[1.1fr_0.9fr]">
        <div className="space-y-4">
          <ChatInput onSend={runRecommendation} loading={isLoading} />
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
                onTrustChipClick={({ hospitalName, trustKind, source, evidence }) =>
                  setSourceModal({
                    open: true,
                    title: `${hospitalName} - ${trustKind}`,
                    evidence: source,
                    details: evidence,
                  })
                }
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
