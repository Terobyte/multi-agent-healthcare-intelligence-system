// SSE-driven reasoning panel — listens to /sse with the canonical event vocab
// from Tero Block 33: triage|extractor|validator|router|transfer|stream_tick|
// ping|done|error. Drops `ping` (heartbeat-only). Closes on `done` or `error`.
//
// EventSource cannot send custom headers, which is why /sse is left unprotected
// while /book + /outcome go through X-Demo-Key (Tero Block 35c).

import { motion } from "framer-motion";
import { useEffect, useRef, useState } from "react";
import { SSE_DEMO_URL, SSE_URL } from "../api";
import type { ReasoningPanelEvent } from "../lib/types";

type Status = "idle" | "streaming" | "done" | "error";

type StreamedEvent = ReasoningPanelEvent & { kind: ReasoningPanelEvent["agent"] | "done" | "error" };

// Cap retained events so a noisy LLM (or a long demo session) can't bloat
// React state to the point of OOM. The panel only shows ~10 at a time anyway.
const MAX_EVENTS = 200;
const cap = (xs: StreamedEvent[]) => (xs.length > MAX_EVENTS ? xs.slice(-MAX_EVENTS) : xs);

const COLOR_BY_AGENT: Record<string, string> = {
  triage: "border-blue-500/60",
  extractor: "border-purple-500/60",
  validator: "border-rose-500/60",
  router: "border-emerald-500/60",
  transfer: "border-amber-500/60",
  stream_tick: "border-slate-600",
  done: "border-slate-500",
  error: "border-red-500/80",
};

const AGENT_KINDS: ReasoningPanelEvent["agent"][] = [
  "triage",
  "extractor",
  "validator",
  "router",
  "transfer",
  "stream_tick",
];

interface Props {
  sessionId: string;
  useDemo?: boolean;
}

export default function ReasoningPanelSSE({ sessionId, useDemo }: Props) {
  const [events, setEvents] = useState<StreamedEvent[]>([]);
  const [status, setStatus] = useState<Status>("idle");
  const esRef = useRef<EventSource | null>(null);

  useEffect(() => {
    if (!sessionId) return;
    const url = useDemo ? SSE_DEMO_URL(sessionId) : SSE_URL(sessionId);
    let es: EventSource;
    try {
      es = new EventSource(url);
    } catch {
      setStatus("error");
      return;
    }
    esRef.current = es;
    setStatus("streaming");
    setEvents([]);

    const push = (kind: StreamedEvent["kind"]) => (ev: MessageEvent<string>) => {
      try {
        const data = JSON.parse(ev.data);
        setEvents((prev) => cap([...prev, { ...data, kind }]));
      } catch {
        setEvents((prev) => cap([
          ...prev,
          { agent: (kind as ReasoningPanelEvent["agent"]) ?? "stream_tick", token: ev.data, trace_id: "", ts: "", kind },
        ]));
      }
    };

    // Keep handlers in a registry so cleanup can call removeEventListener for
    // every one we added — defensive for HMR / React Strict-Mode double-mount,
    // even though es.close() detaches them implicitly.
    const handlers: Array<[string, EventListener]> = [];
    const on = (type: string, fn: EventListener) => {
      es.addEventListener(type, fn);
      handlers.push([type, fn]);
    };

    AGENT_KINDS.forEach((k) => on(k, push(k) as EventListener));

    const onDone = (ev: Event) => {
      push("done")(ev as MessageEvent<string>);
      setStatus("done");
      // Explicit done from server — no point keeping the connection open.
      es.close();
    };
    on("done", onDone);

    // Network-level errors arrive as plain `Event` (no .data). EventSource has
    // built-in exponential reconnect, so DO NOT call es.close() here for
    // transient drops — that would kill auto-reconnect and force the user to
    // reload the page. We only flip status to "error" so the UI shows reconnecting.
    // For server-sent `event: error` payloads (which carry .data), treat as
    // terminal: surface the message and close.
    const onError = (ev: Event) => {
      const msg = ev as MessageEvent<string>;
      if (typeof msg.data === "string" && msg.data.length > 0) {
        push("error")(msg);
        setStatus("error");
        es.close();
        return;
      }
      // Transient — let EventSource retry on its own backoff schedule.
      setStatus("error");
    };
    on("error", onError);
    // `ping` events are heartbeat-only (Tero Block 33) — ignore in UI.

    return () => {
      for (const [type, fn] of handlers) {
        try {
          es.removeEventListener(type, fn);
        } catch {
          /* listener already detached */
        }
      }
      try {
        es.close();
      } catch {
        /* already closed */
      }
    };
  }, [sessionId, useDemo]);

  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4 shadow-premium">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-sm font-semibold tracking-wide text-slate-100">Reasoning stream</h3>
        <span
          className={`text-xs ${
            status === "error"
              ? "text-rose-400"
              : status === "streaming"
                ? "text-emerald-300"
                : "text-slate-400"
          }`}
        >
          {status}
        </span>
      </div>

      <div className="max-h-[250px] space-y-2 overflow-y-auto pr-1">
        {events.length === 0 ? (
          <div className="rounded-xl border border-dashed border-slate-700 p-3 text-xs text-slate-400">
            Waiting for stream…
          </div>
        ) : null}
        {events.map((e, i) => (
          <motion.div
            key={i}
            initial={{ opacity: 0, x: 10 }}
            animate={{ opacity: 1, x: 0 }}
            className={`rounded-xl border-l-4 bg-slate-950/80 px-3 py-2 ${COLOR_BY_AGENT[e.kind] ?? COLOR_BY_AGENT.done}`}
          >
            <div className="text-[11px] font-medium uppercase tracking-wider text-slate-400">
              {e.agent || e.kind}
            </div>
            <div className="mt-1 text-sm text-slate-100">{e.token}</div>
          </motion.div>
        ))}
      </div>
    </div>
  );
}
