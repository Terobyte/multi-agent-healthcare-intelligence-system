import { motion } from "framer-motion";
import { Mic, MicOff, SendHorizontal } from "lucide-react";
import { useState } from "react";
import { useSpeechRecognition } from "../hooks/useSpeechRecognition";

interface ChatInputProps {
  onSend: (query: string) => void;
  loading?: boolean;
}

export default function ChatInput({ onSend, loading }: ChatInputProps) {
  const [query, setQuery] = useState("");
  const maxChars = 500;

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

  const displayValue = listening && transcript ? `${query}${query ? " " : ""}${transcript}` : query;

  return (
    <div className="rounded-2xl border border-white/[0.05] bg-[rgba(40,40,42,0.7)] px-3.5 py-3 backdrop-blur-cg-glass">
      <div className="flex items-center gap-2.5">
        <input
          className="h-8 flex-1 bg-transparent text-[13px] text-cg-mist5 placeholder:text-cg-mist4 outline-none"
          placeholder="Chest tightness, age 64, started 30 min ago…"
          value={displayValue}
          onChange={(e) => setQuery(e.target.value.slice(0, maxChars))}
          onKeyDown={(e) => e.key === "Enter" && submit()}
          disabled={loading || listening}
        />
        <button
          type="button"
          onClick={onMicClick}
          disabled={!supported || loading}
          aria-label={
            !supported
              ? "Microphone not supported"
              : listening
                ? "Stop listening"
                : "Start Hindi voice input"
          }
          title={
            !supported
              ? "Web Speech API not available — use Chrome/Edge"
              : listening
                ? "Stop listening"
                : "Speak Hindi (hi-IN)"
          }
          className={
            "flex h-8 w-8 items-center justify-center rounded-full border transition " +
            (!supported
              ? "cursor-not-allowed border-white/[0.06] text-cg-mist4"
              : listening
                ? "border-cg-peach bg-cg-peach/30 text-cg-peach"
                : "border-[rgba(255,176,136,0.25)] bg-[rgba(255,176,136,0.15)] text-cg-peach hover:bg-[rgba(255,176,136,0.22)]")
          }
        >
          {supported ? <Mic size={14} /> : <MicOff size={14} />}
        </button>
        <motion.button
          whileTap={{ scale: 0.97 }}
          type="button"
          onClick={submit}
          disabled={loading || listening || !query.trim()}
          className="flex h-8 items-center gap-1.5 rounded-lg bg-cg-peach-ink px-3 text-[12px] font-semibold text-cg-peach-ctx transition hover:bg-cg-peach-inkHi disabled:cursor-not-allowed disabled:opacity-50"
        >
          <SendHorizontal size={13} />
          {loading ? "Sending…" : "Send"}
        </motion.button>
      </div>
      <div className="mt-1.5 flex items-center justify-between text-[10px]">
        <span className="text-cg-peach/80">
          {listening ? "● listening (hi-IN)" : error ? `mic: ${error}` : ""}
        </span>
        <span className="text-cg-mist4">
          {query.length}/{maxChars}
        </span>
      </div>
    </div>
  );
}
