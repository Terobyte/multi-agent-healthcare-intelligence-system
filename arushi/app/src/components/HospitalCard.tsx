import { motion } from "framer-motion";
import type { Hospital, TrustEvidence } from "../lib/types";
import ConfidenceInterval from "./ConfidenceInterval";
import DemotedBadge from "./DemotedBadge";
import GreenPulse from "./GreenPulse";

interface HospitalCardProps {
  hospital: Hospital;
  variant?: "lit" | "glass";
  overline?: string;
  onReserve: (hospitalId: string) => void;
  onTrustChipClick: (args: {
    hospitalName: string;
    trustKind: string;
    source: string;
    evidence?: TrustEvidence;
  }) => void;
  reserving?: boolean;
}

const litTrustPill =
  "rounded-full border px-2.5 py-1 text-[10px] font-semibold transition";

const glassTrustPillByKind: Record<string, string> = {
  Bed: "border-[rgba(200,228,208,0.20)] bg-[rgba(200,228,208,0.12)] text-cg-sage",
  Oxygen: "border-[rgba(255,176,136,0.20)] bg-[rgba(255,176,136,0.12)] text-cg-peach",
  Drug: "border-[rgba(255,176,136,0.25)] bg-[rgba(255,176,136,0.18)] text-cg-peach",
  Specialist: "border-white/[0.08] bg-white/[0.06] text-cg-mist1",
};

function isLiveEligible(hospital: Hospital): boolean {
  if (hospital.demoted) return false;
  if (hospital.trustSignals.length === 0) return false;
  const avg =
    hospital.trustSignals.reduce((sum, s) => sum + s.score, 0) /
    hospital.trustSignals.length;
  return avg >= 0.85;
}

export default function HospitalCard({
  hospital,
  variant = "glass",
  overline,
  onReserve,
  onTrustChipClick,
  reserving,
}: HospitalCardProps) {
  if (variant === "lit") {
    return (
      <motion.div
        layout
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        className="cg-lit relative flex flex-col overflow-hidden rounded-cg-card bg-cg-grad-peach p-5 text-cg-peach-ink shadow-cg-peach"
      >
        {overline ? (
          <div className="text-[10px] font-bold uppercase tracking-cg-overline-wide opacity-75">
            {overline}
          </div>
        ) : null}
        <h3 className="mt-1.5 text-[22px] font-bold leading-tight tracking-cg-tight">
          {hospital.name}
        </h3>
        <div className="mt-1 text-[12px] opacity-75">
          {hospital.distanceKm} km · {hospital.etaMinutes} min
        </div>

        {isLiveEligible(hospital) ? (
          <div className="mt-2.5">
            <GreenPulse variant="on-lit" />
          </div>
        ) : null}

        <div className="mt-3 flex flex-wrap gap-1.5">
          {hospital.trustSignals.map((signal) => (
            <button
              key={signal.kind}
              type="button"
              onClick={() =>
                onTrustChipClick({
                  hospitalName: hospital.name,
                  trustKind: signal.kind,
                  source: signal.source,
                  evidence: signal.evidence,
                })
              }
              className={`${litTrustPill} border-white/30 bg-white/[0.18] text-cg-peach-ink hover:bg-white/[0.28]`}
            >
              <span className="mr-1.5">{signal.kind}</span>
              <ConfidenceInterval score={signal.score} ci={signal.ci} variant="on-lit" />
            </button>
          ))}
        </div>

        <div className="mt-auto flex items-end justify-between gap-3 pt-4">
          <div className="text-[44px] font-bold leading-none tracking-cg-num text-cg-peach-ink">
            {hospital.etaMinutes}
            <span className="ml-1 text-[15px] font-medium opacity-70">min</span>
          </div>
          <button
            type="button"
            disabled={reserving}
            onClick={() => onReserve(hospital.id)}
            className="rounded-xl bg-cg-peach-ink px-3.5 py-2.5 text-[12px] font-semibold text-cg-peach-ctx transition hover:bg-cg-peach-inkHi disabled:cursor-not-allowed disabled:opacity-60"
          >
            {reserving ? "Reserving…" : "Reserve a bed →"}
          </button>
        </div>
      </motion.div>
    );
  }

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex flex-col rounded-cg-card border border-white/[0.05] bg-[rgba(35,35,36,0.85)] p-4 text-cg-mist5 backdrop-blur-cg-glass transition hover:border-white/[0.12]"
    >
      <div className="flex items-center gap-2">
        {overline ? (
          <div className="text-[10px] font-semibold uppercase tracking-cg-overline text-cg-mist4">
            {overline}
          </div>
        ) : null}
        {hospital.demoted ? <DemotedBadge /> : null}
      </div>
      <h3 className="mt-1.5 text-[16px] font-semibold tracking-[-0.01em] text-cg-ivory">
        {hospital.name}
      </h3>
      <div className="mt-1 text-[11px] text-cg-mist3">
        {hospital.distanceKm} km · {hospital.etaMinutes} min
      </div>

      <div className="mt-3 flex flex-wrap gap-1.5">
        {hospital.trustSignals.map((signal) => (
          <button
            key={signal.kind}
            type="button"
            onClick={() =>
              onTrustChipClick({
                hospitalName: hospital.name,
                trustKind: signal.kind,
                source: signal.source,
                evidence: signal.evidence,
              })
            }
            className={`rounded-full border px-2.5 py-1 text-[10px] font-semibold transition hover:brightness-125 ${
              glassTrustPillByKind[signal.kind] ?? glassTrustPillByKind.Specialist
            }`}
          >
            <span className="mr-1.5">{signal.kind}</span>
            <ConfidenceInterval score={signal.score} ci={signal.ci} />
          </button>
        ))}
      </div>

      <div className="mt-auto pt-4 text-[32px] font-bold leading-none tracking-cg-num text-cg-ivory">
        {hospital.etaMinutes}
        <span className="ml-1 text-[13px] font-medium text-cg-mist3">min</span>
      </div>

      <button
        type="button"
        disabled={reserving}
        onClick={() => onReserve(hospital.id)}
        className="mt-3 self-start rounded-lg bg-white/[0.08] px-3 py-1.5 text-[11px] font-semibold text-cg-mist5 transition hover:bg-white/[0.14] disabled:cursor-not-allowed disabled:opacity-60"
      >
        {reserving ? "Reserving…" : "Reserve"}
      </button>
    </motion.div>
  );
}
