import { AnimatePresence, motion } from "framer-motion";
import { X } from "lucide-react";
import { useEffect, useId, useRef } from "react";
import type { TrustEvidence } from "../lib/types";

interface SourceModalProps {
  open: boolean;
  title: string;
  evidence: string;
  details?: TrustEvidence;
  onClose: () => void;
}

// Module-level reference counter so stacked modals don't corrupt the
// document.body overflow restore. Only the first opener captures the
// previous overflow; only the last closer restores it.
let modalOpenCount = 0;
let savedBodyOverflow: string | null = null;

function lockBodyScroll() {
  if (modalOpenCount === 0) {
    savedBodyOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
  }
  modalOpenCount += 1;
}

function unlockBodyScroll() {
  modalOpenCount = Math.max(0, modalOpenCount - 1);
  if (modalOpenCount === 0) {
    document.body.style.overflow = savedBodyOverflow ?? "";
    savedBodyOverflow = null;
  }
}

export default function SourceModal({ open, title, evidence, details, onClose }: SourceModalProps) {
  const titleId = useId();
  const closeButtonRef = useRef<HTMLButtonElement | null>(null);
  const dialogRef = useRef<HTMLDivElement | null>(null);

  // Esc-to-close + body scroll lock + focus trap. Both attach only while
  // open so background views stay scrollable normally and listeners don't leak.
  useEffect(() => {
    if (!open) return;

    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        onClose();
        return;
      }
      if (e.key === "Tab") {
        // Focus trap — keep tab cycle inside the dialog.
        const root = dialogRef.current;
        if (!root) return;
        const focusables = root.querySelectorAll<HTMLElement>(
          'a[href], button:not([disabled]), textarea:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])'
        );
        if (focusables.length === 0) {
          e.preventDefault();
          return;
        }
        const first = focusables[0];
        const last = focusables[focusables.length - 1];
        const active = document.activeElement as HTMLElement | null;
        if (e.shiftKey) {
          if (active === first || !root.contains(active)) {
            e.preventDefault();
            last.focus();
          }
        } else {
          if (active === last || !root.contains(active)) {
            e.preventDefault();
            first.focus();
          }
        }
      }
    };
    window.addEventListener("keydown", onKey);

    lockBodyScroll();

    // Move focus into the modal so screen readers and keyboard users land here.
    const focusTimer = window.setTimeout(() => {
      closeButtonRef.current?.focus();
    }, 0);

    return () => {
      window.removeEventListener("keydown", onKey);
      window.clearTimeout(focusTimer);
      unlockBodyScroll();
    };
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
          aria-labelledby={titleId}
        >
          <motion.div
            ref={dialogRef}
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
                <h4 id={titleId} className="mt-1 text-lg font-semibold text-slate-100">{title}</h4>
              </div>
              <button
                ref={closeButtonRef}
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
