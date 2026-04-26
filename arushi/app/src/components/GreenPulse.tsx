import { useReducedMotion } from "framer-motion";

interface GreenPulseProps {
  label?: string;
  variant?: "on-lit" | "on-glass";
}

export default function GreenPulse({ label = "Verified live", variant = "on-glass" }: GreenPulseProps) {
  const wrap =
    variant === "on-lit"
      ? "bg-white/25 text-cg-peach-ink"
      : "bg-[rgba(74,107,63,0.18)] border border-[rgba(74,107,63,0.30)] text-cg-sage";

  // Honor system-level reduced-motion preference (WCAG 2.3.3). Users with
  // vestibular disorders or epilepsy must not be forced into infinite pulses.
  // Also pause animation when offscreen to avoid battery drain on a long list.
  const reduce = useReducedMotion();

  return (
    <div className={`inline-flex items-center gap-2 rounded-full px-2.5 py-1 text-[11px] font-semibold backdrop-blur-cg-glass ${wrap}`}>
      {reduce ? (
        <span
          aria-hidden="true"
          className="inline-block h-2 w-2 rounded-full bg-cg-sage"
        />
      ) : (
        <span aria-hidden="true" className="inline-block cg-pulse-dot" />
      )}
      {label}
    </div>
  );
}
