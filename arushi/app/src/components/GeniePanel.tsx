import { motion } from "framer-motion";
import { Database, Sparkles } from "lucide-react";
import { useState } from "react";
import { api, type GenieResponse } from "../api";

const SAMPLES = [
  "Which states have the most pincodes flagged as specialty deserts?",
  "Find facilities in Bihar with generalSurgery specialty, ranked by trust score",
  "Show 5 facilities where the two LLMs disagreed most, with both reasonings",
];

export default function GeniePanel() {
  const [query, setQuery] = useState("");
  const [response, setResponse] = useState<GenieResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const ask = async (q: string) => {
    const trimmed = q.trim();
    if (!trimmed) return;
    setIsLoading(true);
    setErrorMessage(null);
    setResponse(null);
    try {
      const out = await api.genie(trimmed);
      setResponse(out);
    } catch (err) {
      setErrorMessage(
        err instanceof Error ? err.message : "Genie query failed",
      );
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <motion.section
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="rounded-2xl border border-[#E87B43]/40 bg-[#1A0E07] p-5 text-[#F5E9DD] shadow-lg"
    >
      <header className="mb-4 flex items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2 text-[#FFB088]">
            <Sparkles className="h-4 w-4" />
            <span className="text-xs font-semibold uppercase tracking-wide">
              Ask the data — Databricks Genie
            </span>
          </div>
          <h2 className="mt-1 text-lg font-semibold text-[#F5E9DD]">
            Natural-language query over the Lakehouse
          </h2>
          <p className="mt-1 max-w-2xl text-xs text-[#C9B6A1]">
            Live SQL generation against{" "}
            <code className="text-[#FFB088]">gold_trust_final</code>,{" "}
            <code className="text-[#FFB088]">gold_pin_capabilities</code>,{" "}
            <code className="text-[#FFB088]">gold_trust_two_model</code>.
          </p>
        </div>
        <span
          className={`whitespace-nowrap rounded-full px-2 py-1 text-[10px] font-semibold uppercase tracking-wide ${
            response?.source === "live"
              ? "bg-[#87A878]/20 text-[#C8E4D0] border border-[#87A878]/40"
              : "bg-[#5A5550]/30 text-[#C9B6A1] border border-[#5A5550]"
          }`}
        >
          {response?.source === "live" ? "● live genie" : "○ awaiting"}
        </span>
      </header>

      <div className="flex flex-col gap-2 sm:flex-row">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !isLoading) ask(query);
          }}
          placeholder="e.g. Which states have the most specialty-desert pincodes?"
          className="flex-1 rounded-lg border border-[#5A5550] bg-[#0F0703] px-3 py-2 text-sm text-[#F5E9DD] placeholder-[#5A5550] focus:border-[#E87B43] focus:outline-none"
          disabled={isLoading}
        />
        <button
          type="button"
          onClick={() => ask(query)}
          disabled={isLoading || !query.trim()}
          className="rounded-lg bg-[#E87B43] px-4 py-2 text-sm font-semibold text-[#1A0E07] transition hover:bg-[#FFB088] disabled:cursor-not-allowed disabled:opacity-50"
        >
          {isLoading ? "Asking…" : "Ask"}
        </button>
      </div>

      <div className="mt-3 flex flex-wrap gap-2">
        {SAMPLES.map((s) => (
          <button
            key={s}
            type="button"
            onClick={() => {
              setQuery(s);
              ask(s);
            }}
            disabled={isLoading}
            className="rounded-full border border-[#5A5550] bg-[#0F0703] px-3 py-1 text-[11px] text-[#C9B6A1] transition hover:border-[#E87B43] hover:text-[#FFB088] disabled:opacity-50"
          >
            {s.length > 60 ? s.slice(0, 57) + "…" : s}
          </button>
        ))}
      </div>

      {errorMessage && (
        <p className="mt-4 rounded-lg border border-red-500/40 bg-red-500/10 p-3 text-xs text-red-300">
          {errorMessage}
        </p>
      )}

      {response && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.25 }}
          className="mt-4 space-y-3"
        >
          {response.explanation && (
            <div className="rounded-lg border border-[#5A5550] bg-[#0F0703] p-3">
              <div className="mb-1 flex items-center gap-1 text-[10px] uppercase tracking-wide text-[#C9B6A1]">
                <Sparkles className="h-3 w-3" /> Genie summary
              </div>
              <p className="whitespace-pre-wrap text-sm leading-relaxed text-[#F5E9DD]">
                {response.explanation}
              </p>
            </div>
          )}

          {response.rows && response.rows.length > 0 && (
            <div className="overflow-hidden rounded-lg border border-[#5A5550] bg-[#0F0703]">
              <div className="flex items-center gap-1 border-b border-[#5A5550] bg-[#1A0E07] px-3 py-2 text-[10px] uppercase tracking-wide text-[#C9B6A1]">
                <Database className="h-3 w-3" /> {response.rows.length} rows from
                Lakehouse
              </div>
              <div className="overflow-x-auto">
                <table className="min-w-full text-xs">
                  <thead className="bg-[#1A0E07] text-[#FFB088]">
                    <tr>
                      {(response.columns ?? []).map((c) => (
                        <th
                          key={c}
                          className="px-3 py-2 text-left font-semibold uppercase tracking-wide"
                        >
                          {c}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {response.rows.map((row, i) => (
                      <tr
                        key={i}
                        className={
                          i % 2 === 0 ? "bg-[#0F0703]" : "bg-[#1A0E07]/40"
                        }
                      >
                        {row.map((cell, j) => (
                          <td
                            key={j}
                            className="px-3 py-2 text-[#F5E9DD]"
                          >
                            {String(cell ?? "")}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {response.sql && (
            <details className="rounded-lg border border-[#5A5550] bg-[#0F0703] p-3 text-xs">
              <summary className="cursor-pointer text-[#C9B6A1] hover:text-[#FFB088]">
                Generated SQL
              </summary>
              <pre className="mt-2 overflow-x-auto whitespace-pre-wrap text-[11px] text-[#FFB088]">
                {response.sql}
              </pre>
            </details>
          )}
        </motion.div>
      )}
    </motion.section>
  );
}
