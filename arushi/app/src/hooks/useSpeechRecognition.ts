/**
 * Web Speech API hook (Hindi voice input — Block 11 of requirements3.md).
 *
 * Returns `supported: false` on browsers without webkitSpeechRecognition
 * (Firefox, Safari < 14.1). Caller should disable the mic UI in that case
 * rather than letting `start()` no-op silently.
 *
 * Interim results stream into `transcript` so the input field shows live
 * partial recognition; the final result fires `onFinal` once and stops.
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
      setTranscript((prev) => (finalText ? prev + finalText : interimText || prev));
      if (finalText && onFinalRef.current) {
        onFinalRef.current(finalText.trim());
      }
    };
    rec.onerror = (e: any) => {
      // 'no-speech' / 'aborted' are expected during normal stop — surface only real failures.
      const msg = e?.error || "speech recognition failed";
      if (msg !== "no-speech" && msg !== "aborted") setError(msg);
      setListening(false);
    };
    rec.onend = () => setListening(false);

    recRef.current = rec;
    return () => {
      try {
        rec.stop();
      } catch {
        /* already stopped */
      }
      recRef.current = null;
    };
  }, [lang]);

  const start = useCallback(() => {
    const rec = recRef.current;
    if (!rec || listening) return;
    setError(null);
    setTranscript("");
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
