import { motion, useReducedMotion } from "framer-motion";

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
        <motion.span
          aria-hidden="true"
          className="inline-block h-2 w-2 rounded-full bg-cg-sage"
          initial={{ opacity: 0.6, scale: 1 }}
          whileInView={{
            opacity: [0.6, 1, 0.6],
            scale: [1, 1.25, 1],
            transition: { duration: 1.6, repeat: Infinity, ease: "easeInOut" },
          }}
          viewport={{ once: false, amount: 0.1 }}
        />
      )}
      {label}
    </div>
  );
}
