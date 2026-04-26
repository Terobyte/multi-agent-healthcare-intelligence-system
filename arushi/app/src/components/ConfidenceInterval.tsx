interface Props {
  score: number | undefined | null;
  ci: number | undefined | null;
  variant?: "on-lit" | "on-glass";
}

export default function ConfidenceInterval({ score, ci, variant = "on-glass" }: Props) {
  const muted = variant === "on-lit" ? "opacity-60" : "text-cg-mist4";
  // Defensive defaults — adapter may emit signals without a ci field when the
  // backend trust score is point-estimate only. Crashing the whole HospitalCard
  // tree just because one signal lacks ci is too fragile for a demo.
  const s = typeof score === "number" ? score : 0;
  const c = typeof ci === "number" ? ci : 0;
  return (
    <span className="text-[10px] font-semibold">
      {s.toFixed(2)} <span className={muted}>± {c.toFixed(2)}</span>
    </span>
  );
}
