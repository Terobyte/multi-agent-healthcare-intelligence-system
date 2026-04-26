import { motion } from "framer-motion";

export interface RenderedReasoningRow {
  id: string;
  agent: "Routing Agent" | "Risk Agent" | "Verification Agent";
  text: string;
}

const borderByAgent = {
  "Routing Agent": "border-indigo-500/60",
  "Risk Agent": "border-rose-500/60",
  "Verification Agent": "border-emerald-500/60",
};

export default function ReasoningPanel({ rows, loading }: { rows: RenderedReasoningRow[]; loading?: boolean }) {
  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4 shadow-premium">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-sm font-semibold tracking-wide text-slate-100">Reasoning stream</h3>
        {loading ? <div className="text-xs text-emerald-300">Live</div> : <div className="text-xs text-slate-400">Idle</div>}
      </div>

      <div className="max-h-[250px] space-y-3 overflow-y-auto pr-1">
        {rows.length === 0 && (
          <div className="rounded-xl border border-dashed border-slate-700 p-4 text-sm text-slate-400">
            Ask for placement recommendations to see agent reasoning.
          </div>
        )}

        {rows.map((row) => (
          <motion.div
            key={row.id}
            initial={{ opacity: 0, x: 10 }}
            animate={{ opacity: 1, x: 0 }}
            className={`rounded-xl border bg-slate-950/80 p-3 ${borderByAgent[row.agent]}`}
          >
            <div className="mb-1 text-xs font-medium text-slate-300">{row.agent}</div>
            <div className="text-sm leading-relaxed text-slate-100">{row.text}</div>
          </motion.div>
        ))}
      </div>
    </div>
  );
}
