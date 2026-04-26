/**
 * Web Speech API hook (Hindi voice input — Block 11 of requirements3.md).
 *
 * Returns `supported: false` on browsers without webkitSpeechRecognition
 * (Firefox, Safari < 14.1). Caller should disable the mic UI in that case
 * rather than letting `start()` no-op silently.
 *
 * Interim results stream into `transcript` so the input field shows live
 * partial recognition; final chunks accumulate locally and the consolidated
 * text is delivered through `onFinal` exactly once when the session ends —
 * this avoids duplicate appends in callers when continuous mode produces
 * multiple final results in a single session.
 */
import { useCallback, useEffect, useRef, useState } from "react";

// Web Speech API types are still vendor-prefixed in TypeScript's lib.dom.
// Minimal typing to avoid pulling in `@types/dom-speech-recognition`.
type SR = {
  lang: string;
  interimResults: boolean;
  continuous: boolean;
  onresult: ((e: any) => void) | null;
  onerror: ((e: any) => void) | null;
  onend: (() => void) | null;
  start: () => void;
  stop: () => void;
};

declare global {
  interface Window {
    SpeechRecognition?: new () => SR;
    webkitSpeechRecognition?: new () => SR;
  }
}

interface UseSpeechRecognitionArgs {
  lang?: string;
  onFinal?: (text: string) => void;
}

export function useSpeechRecognition({
  lang = "hi-IN",
  onFinal,
}: UseSpeechRecognitionArgs = {}) {
  const [supported, setSupported] = useState(false);
  const [listening, setListening] = useState(false);
  const [transcript, setTranscript] = useState("");
  const [error, setError] = useState<string | null>(null);
  const recRef = useRef<SR | null>(null);
  const onFinalRef = useRef(onFinal);
  // Per-session accumulator for finalized chunks. Reset on start, drained on end.
  const finalBufferRef = useRef("");

  // Keep latest onFinal without re-creating the recognition instance on every render.
  useEffect(() => {
    onFinalRef.current = onFinal;
  }, [onFinal]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const Ctor = window.SpeechRecognition ?? window.webkitSpeechRecognition;
    if (!Ctor) {
      setSupported(false);
      return;
    }
    setSupported(true);

    const rec = new Ctor();
    rec.lang = lang;
    rec.interimResults = true;
    rec.continuous = false;

    rec.onresult = (e: any) => {
      let finalText = "";
      let interimText = "";
      for (let i = e.resultIndex; i < e.results.length; i++) {
        const r = e.results[i];
        if (r.isFinal) finalText += r[0].transcript;
        else interimText += r[0].transcript;
      }
      if (finalText) {
        finalBufferRef.current += finalText;
        // Display the consolidated finals (plus any current interim suffix).
        setTranscript(finalBufferRef.current + (interimText ? " " + interimText : ""));
      } else {
        setTranscript(finalBufferRef.current ? finalBufferRef.current + " " + interimText : interimText);
      }
    };
    rec.onerror = (e: any) => {
      // 'no-speech' / 'aborted' are expected during normal stop — surface only real failures.
      const msg = e?.error || "speech recognition failed";
      if (msg !== "no-speech" && msg !== "aborted") setError(msg);
      setListening(false);
    };
    rec.onend = () => {
      // Drain the accumulated finals exactly once per session.
      const consolidated = finalBufferRef.current.trim();
      finalBufferRef.current = "";
      if (consolidated && onFinalRef.current) {
        onFinalRef.current(consolidated);
      }
      setListening(false);
    };

    recRef.current = rec;
    return () => {
      // Null handlers BEFORE stop() so the in-flight final/end events don't
      // fire stale callbacks against an unmounted caller.
      rec.onresult = null;
      rec.onerror = null;
      rec.onend = null;
      try {
        rec.stop();
      } catch {
        /* already stopped */
      }
      recRef.current = null;
      finalBufferRef.current = "";
    };
  }, [lang]);

  const start = useCallback(() => {
    const rec = recRef.current;
    if (!rec || listening) return;
    setError(null);
    setTranscript("");
    finalBufferRef.current = "";
    try {
      rec.start();
      setListening(true);
    } catch (e) {
      // start() throws if called twice quickly — surface as error, don't crash UI.
      setError(e instanceof Error ? e.message : "failed to start mic");
    }
  }, [listening]);

  const stop = useCallback(() => {
    recRef.current?.stop();
  }, []);

  return { supported, listening, transcript, error, start, stop };
}
