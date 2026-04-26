import { Mic, SendHorizontal } from "lucide-react";
import { useState } from "react";
import { motion } from "framer-motion";

interface ChatInputProps {
  onSend: (query: string) => void;
  loading?: boolean;
}

export default function ChatInput({ onSend, loading }: ChatInputProps) {
  const [query, setQuery] = useState("");
  // Real medical intake descriptions can run several sentences (symptoms +
  // duration + meds + history) — 180 was too tight for actual demo prompts.
  const maxChars = 500;

  const submit = () => {
    const trimmed = query.trim();
    if (!trimmed) return;
    onSend(trimmed);
    setQuery("");
  };

  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-3 shadow-premium">
      <div className="mb-2 text-xs uppercase tracking-widest text-slate-400">Patient intake prompt</div>
      <div className="flex items-center gap-2">
        <input
          className="h-11 flex-1 rounded-xl border border-slate-700 bg-slate-950 px-4 text-sm text-slate-100 outline-none transition focus:border-indigo-500"
          placeholder="eg. Need trauma center with oxygen + specialist in under 25 mins..."
          value={query}
          onChange={(e) => setQuery(e.target.value.slice(0, maxChars))}
          onKeyDown={(e) => e.key === "Enter" && submit()}
          disabled={loading}
        />
        <button
          className="flex h-11 w-11 items-center justify-center rounded-xl border border-slate-700 text-slate-300 transition hover:border-indigo-500 hover:text-indigo-400"
          aria-label="Microphone"
          type="button"
        >
          <Mic size={18} />
        </button>
        <motion.button
          whileTap={{ scale: 0.97 }}
          className="flex h-11 items-center gap-2 rounded-xl bg-indigo-500 px-4 text-sm font-medium text-white transition hover:bg-indigo-400 disabled:cursor-not-allowed disabled:opacity-50"
          onClick={submit}
          disabled={loading}
          type="button"
        >
          <SendHorizontal size={16} />
          {loading ? "Sending..." : "Send"}
        </motion.button>
      </div>
      <div className="mt-2 text-right text-[11px] text-slate-500">{query.length}/{maxChars}</div>
    </div>
  );
}
