import { AnimatePresence, motion } from "framer-motion";
import { X } from "lucide-react";
import { useEffect } from "react";
import type { TrustEvidence } from "../lib/types";

interface SourceModalProps {
  open: boolean;
  title: string;
  evidence: string;
  details?: TrustEvidence;
  onClose: () => void;
}

export default function SourceModal({ open, title, evidence, details, onClose }: SourceModalProps) {
  // Esc-to-close — universal modal keyboard affordance. Only attaches the
  // listener while the modal is actually open so background views stay clean.
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/75 p-4 backdrop-blur-sm"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={onClose}
          role="dialog"
          aria-modal="true"
          aria-labelledby="source-modal-title"
        >
          <motion.div
            className="w-full max-w-lg rounded-2xl border border-slate-700 bg-slate-900 p-5 shadow-premium"
            initial={{ opacity: 0, y: 12, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 8, scale: 0.98 }}
            transition={{ duration: 0.2 }}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="mb-4 flex items-start justify-between gap-3">
              <div>
                <div className="text-xs uppercase tracking-widest text-indigo-300">Source trace</div>
                <h4 id="source-modal-title" className="mt-1 text-lg font-semibold text-slate-100">{title}</h4>
              </div>
              <button
                type="button"
                onClick={onClose}
                className="rounded-lg border border-slate-700 p-1.5 text-slate-300 transition hover:border-slate-500 hover:text-white"
                aria-label="Close source modal"
              >
                <X size={16} />
              </button>
            </div>
            <div className="rounded-xl border border-slate-800 bg-slate-950/70 p-4 text-sm leading-relaxed text-slate-300">
              <p>{details?.summary ?? evidence}</p>
              <div className="mt-4 space-y-1.5 text-xs text-slate-400">
                {details?.method ? (
                  <div>
                    <span className="text-slate-500">Method: </span>
                    <span>{details.method}</span>
                  </div>
                ) : null}
                {details?.sourceId ? (
                  <div>
                    <span className="text-slate-500">Source ID: </span>
                    <span>{details.sourceId}</span>
                  </div>
                ) : null}
                {details?.lastUpdatedAt ? (
                  <div>
                    <span className="text-slate-500">Last updated: </span>
                    <span>{new Date(details.lastUpdatedAt).toLocaleString()}</span>
                  </div>
                ) : null}
              </div>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
