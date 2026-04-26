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
  // "ok"       → validator ran for top-1 hospital AND both models agreed →
  //              green "Verified live" pulse.
  // "skipped"  → validator was not called (confidence ≥ 0.7) or models
  //              disagreed → amber "Validation skipped" badge.
  // undefined  → card is not the top-1 candidate; no validation badge shown.
  validatorStatus?: "ok" | "skipped";
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
  validatorStatus,
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
  const shadowEligible = liveEligible && avgTrust >= 0.89;
  const cardPadding = liveEligible ? "p-[22px]" : hospital.demoted ? "p-4" : "p-[18px]";
  const litClass = shadowEligible
    ? "border-[rgba(200,228,208,0.18)] shadow-[0_12px_30px_rgba(135,168,120,0.16)]"
    : "border-white/[0.05]";

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.22, ease: [0.22, 1, 0.36, 1] }}
      className={`rounded-cg-card border bg-[rgba(35,35,36,0.85)] backdrop-blur-cg-glass transition-[transform,border-color,background-color] duration-[180ms] ease-out hover:-translate-y-0.5 hover:border-white/[0.12] ${cardPadding} ${litClass}`}
    >
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="text-base font-bold leading-[1.18] tracking-[-0.015em] text-cg-ivory">
              {hospital.name}
            </h3>
            {hospital.demoted ? <DemotedBadge /> : null}
          </div>
          <div className="mt-1.5 flex flex-wrap items-center gap-3 text-xs text-cg-mist2 tabular-nums">
            <span className="inline-flex items-center gap-1">
              <MapPin size={13} />
              {hospital.distanceKm} km
            </span>
            <span className="inline-flex items-center gap-1">
              <Clock3 size={13} />
              {hospital.etaMinutes} min
            </span>
          </div>
          {liveEligible && validatorStatus === "ok" ? (
            // Green pulse: live-data badge — requires liveEligible.
            <div className="mt-2">
              <GreenPulse />
            </div>
          ) : validatorStatus === "skipped" ? (
            // Amber badge: pipeline-metadata badge — shows whenever the top-1
            // card received validator_status="skipped", regardless of liveEligible.
            // Cards 2-N receive validatorStatus=undefined so they show nothing.
            <div className="mt-2">
              <span
                role="status"
                aria-label="Validation skipped — high triage confidence; no two-model check performed"
                className="inline-flex items-center gap-1 rounded-full border border-amber-500/30 bg-amber-500/10 px-2.5 py-1 text-[11px] font-semibold text-amber-400"
              >
                <span aria-hidden="true" className="inline-block h-2 w-2 rounded-full bg-amber-400 opacity-70" />
                Validation skipped
              </span>
            </div>
          ) : null}
        </div>
        <button
          type="button"
          disabled={reserving}
          onClick={() => onReserve(hospital.id)}
          // Loud peach CTA — design rule says only ONE high-saturation peach
          // surface per view, but the lit-card hero variant was reverted to a
          // uniform list, so the CTA carries the urgency now without adding a
          // second lit surface.
          className="shrink-0 rounded-xl bg-cg-peach px-4 py-2.5 text-sm font-bold text-cg-peach-ink transition duration-[180ms] ease-out hover:-translate-y-px hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {reserving ? "Reserving…" : "Reserve →"}
        </button>
      </div>

      <div className="mt-4 flex flex-wrap gap-2">
        {hospital.trustSignals.map((signal) => (
          <motion.button
            key={signal.kind}
            type="button"
            whileHover={{ y: -1 }}
            transition={{ duration: 0.18, ease: "easeOut" }}
            className={`min-w-0 rounded-full border px-3 py-1.5 text-xs font-semibold leading-none transition ${
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
