import { AlertTriangle } from "lucide-react";

export default function DemotedBadge() {
  // role=status + aria-label so screen readers announce the demotion context,
  // not just the orange pill. WCAG 1.4.1: do not rely on color alone — the
  // warning triangle gives a non-color signal for color-blind / mono-display
  // users.
  return (
    <span
      role="status"
      aria-label="Demoted: this hospital ranked lower due to low trust signals"
      className="inline-flex items-center gap-1 rounded-full border border-[rgba(194,82,43,0.40)] bg-[rgba(194,82,43,0.20)] px-2 py-0.5 text-[10px] font-bold uppercase tracking-cg-overline text-cg-peach"
    >
      <AlertTriangle size={10} aria-hidden="true" />
      DEMOTED
    </span>
  );
}
