import { Mic, MicOff, SendHorizontal } from "lucide-react";
import { useState } from "react";
import { motion } from "framer-motion";
import { useSpeechRecognition } from "../hooks/useSpeechRecognition";

interface ChatInputProps {
  onSend: (query: string) => void;
  loading?: boolean;
}

export default function ChatInput({ onSend, loading }: ChatInputProps) {
  const [query, setQuery] = useState("");
  // Real medical intake descriptions can run several sentences (symptoms +
  // duration + meds + history) — 180 was too tight for actual demo prompts.
  const maxChars = 500;

  // Block 11 — Hindi voice input. Final transcript appends to whatever the
  // user has typed so far rather than replacing, so they can mix typing + voice.
  const { supported, listening, transcript, error, start, stop } = useSpeechRecognition({
    lang: "hi-IN",
    onFinal: (final) => {
      setQuery((prev) => {
        const merged = (prev ? prev.trim() + " " : "") + final;
        return merged.slice(0, maxChars);
      });
    },
  });

  const submit = () => {
    const trimmed = query.trim();
    if (!trimmed) return;
    onSend(trimmed);
    setQuery("");
  };

  const onMicClick = () => {
    if (!supported) return;
    if (listening) stop();
    else start();
  };

  // While listening, overlay the live (interim) transcript so the user sees
  // what the API thinks they said. The final result merges via onFinal above.
  const displayValue = listening && transcript ? `${query}${query ? " " : ""}${transcript}` : query;

  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-3 shadow-premium">
      <div className="mb-2 flex items-center justify-between">
        <div className="text-xs uppercase tracking-widest text-slate-400">Patient intake prompt</div>
        {listening && (
          <div className="flex items-center gap-1.5 text-[11px] text-rose-400">
            <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-rose-500" />
            listening (hi-IN)
          </div>
        )}
      </div>
      <div className="flex items-center gap-2">
        <input
          className="h-11 flex-1 rounded-xl border border-slate-700 bg-slate-950 px-4 text-sm text-slate-100 outline-none transition focus:border-indigo-500"
          placeholder="eg. Need trauma center with oxygen + specialist in under 25 mins..."
          value={displayValue}
          onChange={(e) => setQuery(e.target.value.slice(0, maxChars))}
          onKeyDown={(e) => e.key === "Enter" && submit()}
          disabled={loading || listening}
        />
        <button
          className={
            "flex h-11 w-11 items-center justify-center rounded-xl border transition " +
            (!supported
              ? "cursor-not-allowed border-slate-800 text-slate-600"
              : listening
                ? "border-rose-500 bg-rose-500/10 text-rose-400 hover:border-rose-400"
                : "border-slate-700 text-slate-300 hover:border-indigo-500 hover:text-indigo-400")
          }
          aria-label={
            !supported
              ? "Microphone not supported in this browser"
              : listening
                ? "Stop listening"
                : "Start Hindi voice input"
          }
          title={
            !supported
              ? "Web Speech API not available — use Chrome/Edge for voice input"
              : listening
                ? "Stop listening"
                : "Speak Hindi (hi-IN)"
          }
          type="button"
          onClick={onMicClick}
          disabled={!supported || loading}
        >
          {supported ? <Mic size={18} /> : <MicOff size={18} />}
        </button>
        <motion.button
          whileTap={{ scale: 0.97 }}
          className="flex h-11 items-center gap-2 rounded-xl bg-indigo-500 px-4 text-sm font-medium text-white transition hover:bg-indigo-400 disabled:cursor-not-allowed disabled:opacity-50"
          onClick={submit}
          disabled={loading || listening}
          type="button"
        >
          <SendHorizontal size={16} />
          {loading ? "Sending..." : "Send"}
        </motion.button>
      </div>
      <div className="mt-2 flex items-center justify-between text-[11px]">
        <span className="text-rose-400/80">{error ? `mic: ${error}` : ""}</span>
        <span className="text-slate-500">{query.length}/{maxChars}</span>
      </div>
    </div>
  );
}
