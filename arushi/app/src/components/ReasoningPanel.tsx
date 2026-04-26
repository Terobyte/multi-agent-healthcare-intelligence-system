import { motion } from "framer-motion";

export interface RenderedReasoningRow {
  id: string;
  agent: "Routing Agent" | "Risk Agent" | "Verification Agent";
  text: string;
}

const shortName: Record<RenderedReasoningRow["agent"], string> = {
  "Routing Agent": "Routing",
  "Risk Agent": "Risk",
  "Verification Agent": "Verify",
};

export default function ReasoningPanel({
  rows,
  loading,
}: {
  rows: RenderedReasoningRow[];
  loading?: boolean;
}) {
  return (
    <div className="rounded-cg-card border border-white/[0.05] bg-[rgba(20,20,21,0.6)] px-4 py-4 backdrop-blur-cg-glass">
      <div className="flex items-center justify-between gap-3">
        <div className="cg-overline-rule text-[10px] font-semibold uppercase tracking-cg-overline text-cg-mist4">
          Why this recommendation
        </div>
        <div className={`cg-overline-rule cg-overline-rule-sage text-[10px] font-semibold uppercase tracking-cg-overline ${loading ? "text-cg-sage" : "text-cg-mist4"}`}>
          {loading ? "live" : "idle"}
        </div>
      </div>

      <div className="mt-3 max-h-[240px] space-y-2.5 overflow-y-auto pr-1">
        {rows.length === 0 ? (
          <div className="rounded-cg-tile border border-dashed border-white/[0.08] px-3 py-3 text-[12px] text-cg-mist3">
            {loading
              ? "Triaging symptoms and waiting for the first agent note."
              : "Ask for placement recommendations to see agent reasoning."}
          </div>
        ) : null}

        {rows.map((row) => (
          <motion.div
            key={row.id}
            initial={{ opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.22 }}
            className="grid grid-cols-[78px_minmax(0,1fr)] items-start gap-2.5 text-[12px] leading-[1.5] text-cg-mist1 max-sm:grid-cols-1 max-sm:gap-0.5"
          >
            <div className="font-semibold text-cg-peach">
              {shortName[row.agent]}
            </div>
            <div className="min-w-0">{row.text}</div>
          </motion.div>
        ))}
      </div>
    </div>
  );
}
