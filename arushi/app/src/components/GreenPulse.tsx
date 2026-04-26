interface GreenPulseProps {
  label?: string;
  variant?: "on-lit" | "on-glass";
}

export default function GreenPulse({ label = "Verified live", variant = "on-glass" }: GreenPulseProps) {
  const wrap =
    variant === "on-lit"
      ? "bg-white/25 text-cg-peach-ink"
      : "bg-[rgba(74,107,63,0.18)] border border-[rgba(74,107,63,0.30)] text-cg-sage";
  return (
    <div className={`inline-flex items-center gap-2 rounded-full px-2.5 py-1 text-[11px] font-semibold backdrop-blur-cg-glass ${wrap}`}>
      <span className="cg-pulse-dot" />
      {label}
    </div>
  );
}
