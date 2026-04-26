import { motion } from "framer-motion";
import { Clock3, MapPin } from "lucide-react";
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

const trustColorMap: Record<string, string> = {
  Bed: "border-indigo-500/60 text-indigo-300",
  Oxygen: "border-emerald-500/60 text-emerald-300",
  Drug: "border-rose-500/60 text-rose-300",
  Specialist: "border-slate-500/60 text-slate-200",
};

export default function HospitalCard({
  hospital,
  onReserve,
  onTrustChipClick,
  reserving,
}: HospitalCardProps) {
  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-2xl border border-slate-800 bg-slate-900/70 p-4 shadow-premium"
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="text-base font-semibold text-slate-100">{hospital.name}</h3>
            {hospital.demoted ? <DemotedBadge /> : null}
          </div>
          <div className="mt-2 flex flex-wrap items-center gap-3 text-xs text-slate-400">
            <span className="inline-flex items-center gap-1">
              <MapPin size={13} />
              {hospital.distanceKm} km
            </span>
            <span className="inline-flex items-center gap-1">
              <Clock3 size={13} />
              {hospital.etaMinutes} min
            </span>
          </div>
          <div className="mt-2">
            <GreenPulse />
          </div>
        </div>
        <button
          type="button"
          disabled={reserving}
          onClick={() => onReserve(hospital.id)}
          className="rounded-xl bg-emerald-500 px-3 py-2 text-xs font-semibold text-slate-950 transition hover:bg-emerald-400 disabled:cursor-not-allowed disabled:opacity-60"
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
            className={`rounded-full border px-3 py-1 text-xs transition ${trustColorMap[signal.kind] ?? "border-slate-700 text-slate-300"}`}
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
