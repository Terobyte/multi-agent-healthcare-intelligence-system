import { motion } from "framer-motion";
import { Mic, MicOff, SendHorizontal } from "lucide-react";
import { useRef, useState } from "react";
import { useSpeechRecognition } from "../hooks/useSpeechRecognition";

interface ChatInputProps {
  onSend: (query: string) => void;
  loading?: boolean;
}

export default function ChatInput({ onSend, loading }: ChatInputProps) {
  const [query, setQuery] = useState("");
  const [truncationWarning, setTruncationWarning] = useState<string | null>(null);
  const submitTimerRef = useRef<number | null>(null);
  const maxChars = 500;

  const { supported, listening, transcript, error, start, stop } = useSpeechRecognition({
    lang: "hi-IN",
    onFinal: (final) => {
      setQuery((prev) => {
        const base = prev.trimEnd();
        const merged = base + (base ? " " : "") + final;
        if (merged.length > maxChars) {
          setTruncationWarning("Voice input truncated to fit 500-char limit");
          return merged.slice(0, maxChars);
        }
        return merged;
      });
    },
  });

  const submit = (text?: string) => {
    const candidate = (text ?? query).trim();
    if (!candidate) return;
    onSend(candidate);
    setQuery("");
    setTruncationWarning(null);
  };

  const handleEnter = () => {
    if (loading) return;
    if (listening) {
      // Mid-utterance Enter: stop the mic and wait briefly so the final
      // transcript chunk has a chance to land before we submit.
      stop();
      if (submitTimerRef.current !== null) {
        window.clearTimeout(submitTimerRef.current);
      }
      submitTimerRef.current = window.setTimeout(() => {
        submitTimerRef.current = null;
        submit();
      }, 250);
      return;
    }
    submit();
  };

  const onMicClick = () => {
    if (!supported) return;
    if (listening) stop();
    else {
      setTruncationWarning(null);
      start();
    }
  };

  // Avoid double-spacing if the user already typed a trailing space.
  const displayValue =
    listening && transcript
      ? `${query.trimEnd()}${query.trim() ? " " : ""}${transcript}`
      : query;

  const statusLine = loading
    ? "Triaging your symptoms..."
    : listening
      ? "● listening (hi-IN)"
      : truncationWarning
        ? truncationWarning
        : error
          ? `mic: ${error}`
          : "";

  return (
    <div className="rounded-cg-card border border-white/[0.05] bg-[rgba(40,40,42,0.7)] px-[18px] py-4 backdrop-blur-cg-glass">
      <div className="flex flex-wrap items-center gap-2.5">
        <input
          className="h-8 min-w-0 flex-[1_1_100%] bg-transparent text-[13px] text-cg-mist5 placeholder:text-cg-mist4 outline-none sm:flex-1"
          placeholder="Chest tightness, age 64, started 30 min ago…"
          value={displayValue}
          onChange={(e) => {
            setTruncationWarning(null);
            setQuery(e.target.value.slice(0, maxChars));
          }}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              handleEnter();
            }
          }}
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
            "flex h-8 w-10 flex-none items-center justify-center rounded-full border transition hover:-translate-y-px sm:w-8 " +
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
          onClick={() => submit()}
          disabled={loading || listening || !query.trim()}
          className="flex h-8 flex-1 items-center justify-center gap-1.5 rounded-lg bg-cg-peach-ink px-3 text-[12px] font-semibold text-cg-peach-ctx transition hover:-translate-y-px hover:bg-cg-peach-inkHi disabled:cursor-not-allowed disabled:opacity-50 sm:flex-none"
        >
          <SendHorizontal size={13} />
          {loading ? "Sending…" : "Send"}
        </motion.button>
      </div>
      <div className="mt-1.5 flex items-center justify-between gap-3 text-[10px]">
        <span className="text-cg-peach/80">{statusLine}</span>
        <span className="shrink-0 text-cg-mist4 tabular-nums">
          {query.length}/{maxChars}
        </span>
      </div>
    </div>
  );
}
