import { motion } from "framer-motion";
import { useCallback, useEffect, useRef, useState } from "react";
import AtomicBookingTiles, { type BookingState } from "../components/AtomicBookingTiles";
import ChatInput from "../components/ChatInput";
import HospitalCard from "../components/HospitalCard";
import HospitalMap from "../components/HospitalMap";
import ReasoningPanel, { type RenderedReasoningRow } from "../components/ReasoningPanel";
import SourceModal from "../components/SourceModal";
import { isBackendConfigured, isDegraded, recommend, reserve, streamReasoning } from "../lib/api";
import type { Hospital, TrustEvidence } from "../lib/types";

const agentById: Record<string, RenderedReasoningRow["agent"]> = {
  route_1: "Routing Agent",
  risk_1: "Risk Agent",
  verify_1: "Verification Agent",
};

export default function PatientFlow() {
  const [hospitals, setHospitals] = useState<Hospital[]>([]);
  const [validatorStatus, setValidatorStatus] = useState<"ok" | "skipped">("skipped");
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
  // Separate sequence for reserve flow — rapid double-clicks on different
  // hospitals would otherwise cross-contaminate booking state when responses
  // arrive out of order.
  const reserveSeqRef = useRef(0);
  // Per-instance flag — replaces the previous module-level `_autoQuerySent`
  // which survived unmount/remount across tab switches in App.tsx and blocked
  // auto-query when the user navigated back to the Patient page.
  const autoQuerySentRef = useRef(false);

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
    // Stale-evidence guard — a SourceModal opened against the previous
    // hospital list must not stay mounted while a fresh query refreshes the
    // underlying data. Always close on a new run.
    setSourceModal({ open: false, title: "", evidence: "" });
    try {
      const response = await recommend({ query });
      if (!isMountedRef.current || myReq !== requestSeqRef.current) return;
      setHospitals(response.hospitals);
      setValidatorStatus(response.validator_status ?? "skipped");
      setDegraded(isDegraded());
      await streamReasoning((msgId, token) => {
        if (!isMountedRef.current || myReq !== requestSeqRef.current) return;
        // Re-read degraded on every successful tick so a backend that
        // recovered mid-stream clears the banner instead of staying stuck.
        setDegraded(isDegraded());
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
      autoQuerySentRef.current = false;
      setErrorMessage("Could not fetch recommendations. Try again in a few seconds.");
    } finally {
      // Re-read degraded in finally too — covers the error path where the
      // try-block setDegraded never ran but the backend may now be healthy.
      if (isMountedRef.current && myReq === requestSeqRef.current) {
        setDegraded(isDegraded());
        setIsLoading(false);
      }
    }
  }, []);

  const reserveHospital = useCallback(async (hospitalId: string) => {
    // Race guard — rapid double-clicks (or clicks on different hospitals)
    // must not cross-contaminate booking state. Each call captures its own
    // seq; later calls bump the ref, and any stale resolution becomes a
    // no-op via the seq check below.
    const myReq = ++reserveSeqRef.current;
    bookingTimersRef.current.forEach((id) => window.clearTimeout(id));
    bookingTimersRef.current = [];
    if (myReq !== reserveSeqRef.current) return;
    setReservingId(hospitalId);
    setBookingState("reserving");
    setErrorMessage(null);
    try {
      const result = await reserve({ hospitalId });
      if (!isMountedRef.current || myReq !== reserveSeqRef.current) return;
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
          window.setTimeout(() => {
            if (isMountedRef.current && myReq === reserveSeqRef.current) setBookingState("idle");
          }, 1300),
        );
      } else {
        setBookingState("success");
        bookingTimersRef.current.push(
          window.setTimeout(() => {
            if (isMountedRef.current && myReq === reserveSeqRef.current)
              setBookingState("rollback");
          }, 1800),
          window.setTimeout(() => {
            if (isMountedRef.current && myReq === reserveSeqRef.current) setBookingState("idle");
          }, 2800),
        );
      }
    } catch {
      if (!isMountedRef.current || myReq !== reserveSeqRef.current) return;
      setBookingState("rollback");
      setErrorMessage("Reservation failed. Please retry.");
      bookingTimersRef.current.push(
        window.setTimeout(() => {
          if (isMountedRef.current && myReq === reserveSeqRef.current) setBookingState("idle");
        }, 1300),
      );
    } finally {
      if (isMountedRef.current && myReq === reserveSeqRef.current) setReservingId(null);
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
      // Capture the recommendation seq at click time. If a new recommend()
      // bumped the ref between the synthetic event firing and this handler
      // running, the hospital list is about to refresh and opening a modal
      // against soon-stale evidence would mislead the user.
      const seqAtClick = requestSeqRef.current;
      if (seqAtClick !== requestSeqRef.current) return;
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
    if (autoQuerySentRef.current || hasInitializedRef.current) return;
    hasInitializedRef.current = true;
    autoQuerySentRef.current = true;
    void runRecommendation("Auto triage critical care options nearby.");
  }, [runRecommendation]);

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-6">
      <div className="grid grid-cols-1 gap-4 xl:grid-cols-[1.1fr_0.9fr]">
        <div className="space-y-6">
          <ChatInput onSend={runRecommendation} loading={isLoading} />
          {degraded ? (
            <div className="rounded-cg-tile border border-[rgba(255,176,136,0.30)] bg-[rgba(255,176,136,0.10)] px-4 py-2 text-[12px] text-cg-peach">
              {isBackendConfigured()
                ? "Backend unreachable — showing offline demo data."
                : "Backend URL not configured — showing offline demo data."}
            </div>
          ) : null}
          {errorMessage ? (
            <div className="rounded-cg-tile border border-[rgba(194,82,43,0.40)] bg-[rgba(194,82,43,0.15)] px-4 py-2 text-[13px] text-cg-peach">
              {errorMessage}
            </div>
          ) : null}
          {!isLoading && !errorMessage && hospitals.length === 0 ? (
            <div className="rounded-cg-tile border border-dashed border-white/[0.10] px-4 py-3 text-[13px] text-cg-mist3">
              No hospitals matched this query. Try broader terms.
            </div>
          ) : null}
          <div className="space-y-[14px]">
            {hospitals.map((hospital, idx) => (
              <HospitalCard
                key={hospital.id}
                hospital={hospital}
                onReserve={reserveHospital}
                onTrustChipClick={onTrustChipClick}
                reserving={reservingId === hospital.id}
                validatorStatus={idx === 0 ? validatorStatus : undefined}
              />
            ))}
          </div>
        </div>
        {/* Sticky on xl+ — follows the user as they scroll the long hospital
            list. self-start prevents the grid item from stretching to match
            the left column; max-h + overflow-y-auto keep the panel from ever
            exceeding the viewport so it doesn't block scrolling. */}
        <div className="space-y-6 xl:sticky xl:top-4 xl:self-start xl:max-h-[calc(100vh-2rem)] xl:overflow-y-auto xl:pr-1">
          <HospitalMap hospitals={hospitals} />
          <AtomicBookingTiles
            state={bookingState}
            // Inline trigger — fires the same reserve flow as the per-card
            // Reserve button against the first non-demoted hospital. Lets the
            // user demo the 4-tile match animation without scrolling to a card.
            onTriggerDemo={
              hospitals.length > 0
                ? () => {
                    const target = hospitals.find((h) => !h.demoted) ?? hospitals[0];
                    void reserveHospital(target.id);
                  }
                : undefined
            }
            demoDisabled={hospitals.length === 0 || isLoading}
          />
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
