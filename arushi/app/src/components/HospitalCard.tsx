import { motion } from "framer-motion";
import { Clock3, MapPin } from "lucide-react";
import { memo, useMemo } from "react";
import type { Hospital, TrustEvidence } from "../lib/types";
import ConfidenceInterval from "./ConfidenceInterval";
import DemotedBadge from "./DemotedBadge";
import GreenPulse from "./GreenPulse";

interface HospitalCardProps {
  hospital: Hospital;
  onReserve: (hospitalId: string) => void;
  onTrustChipClick: (args: {
    hospitalName: string;
    trustKind: string;
    source: string;
    evidence?: TrustEvidence;
  }) => void;
  reserving?: boolean;
}

const trustPillByKind: Record<string, string> = {
  Bed: "border-[rgba(200,228,208,0.20)] bg-[rgba(200,228,208,0.12)] text-cg-sage",
  Oxygen: "border-[rgba(255,176,136,0.20)] bg-[rgba(255,176,136,0.12)] text-cg-peach",
  Drug: "border-[rgba(255,176,136,0.25)] bg-[rgba(255,176,136,0.18)] text-cg-peach",
  Specialist: "border-white/[0.08] bg-white/[0.06] text-cg-mist1",
};

function HospitalCard({
  hospital,
  onReserve,
  onTrustChipClick,
  reserving,
}: HospitalCardProps) {
  // Tier-1 only — render GreenPulse "verified live" pulse only when the card
  // is NOT demoted AND average trust ≥ 0.85. Otherwise the pulse is misleading:
  // a demoted hospital with a "live" beacon. Memoised so we don't re-walk the
  // trustSignals array on every parent state change.
  const avgTrust = useMemo(() => {
    if (hospital.trustSignals.length === 0) return 0;
    return (
      hospital.trustSignals.reduce((s, x) => s + x.score, 0) /
      hospital.trustSignals.length
    );
  }, [hospital.trustSignals]);

  const liveEligible = !hospital.demoted && avgTrust >= 0.85;

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-cg-card border border-white/[0.05] bg-[rgba(35,35,36,0.85)] p-4 backdrop-blur-cg-glass transition hover:border-white/[0.12]"
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="text-base font-semibold tracking-[-0.01em] text-cg-ivory">
              {hospital.name}
            </h3>
            {hospital.demoted ? <DemotedBadge /> : null}
          </div>
          <div className="mt-2 flex flex-wrap items-center gap-3 text-xs text-cg-mist2">
            <span className="inline-flex items-center gap-1">
              <MapPin size={13} />
              {hospital.distanceKm} km
            </span>
            <span className="inline-flex items-center gap-1">
              <Clock3 size={13} />
              {hospital.etaMinutes} min
            </span>
          </div>
          {liveEligible ? (
            <div className="mt-2">
              <GreenPulse />
            </div>
          ) : null}
        </div>
        <button
          type="button"
          disabled={reserving}
          onClick={() => onReserve(hospital.id)}
          className="rounded-xl bg-cg-peach px-3 py-2 text-xs font-semibold text-cg-peach-ink transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {reserving ? "Reserving..." : "Reserve"}
        </button>
      </div>

      <div className="mt-4 flex flex-wrap gap-2">
        {hospital.trustSignals.map((signal) => (
          <motion.button
            key={signal.kind}
            type="button"
            whileHover={{ y: -1.5 }}
            className={`rounded-full border px-3 py-1 text-xs font-semibold transition ${
              trustPillByKind[signal.kind] ?? trustPillByKind.Specialist
            }`}
            onClick={() =>
              onTrustChipClick({
                hospitalName: hospital.name,
                trustKind: signal.kind,
                source: signal.source,
                evidence: signal.evidence,
              })
            }
          >
            <span className="mr-2">{signal.kind}</span>
            <ConfidenceInterval score={signal.score} ci={signal.ci} />
          </motion.button>
        ))}
      </div>
    </motion.div>
  );
}

// Memoised so a parent re-render (e.g. typing in the query box) doesn't cascade
// through every card in a long list. The default shallow prop comparison is
// sufficient because hospital identity is stable across the parent's useMemo.
export default memo(HospitalCard);
