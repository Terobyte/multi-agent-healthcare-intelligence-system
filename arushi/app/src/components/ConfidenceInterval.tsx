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
  const sRaw = typeof score === "number" ? score : 0;
  const cRaw = typeof ci === "number" ? ci : 0;
  // NaN/Infinity guards: a non-finite score means the upstream trust pipeline
  // produced garbage — render nothing rather than "NaN ± NaN" in the demo.
  if (!Number.isFinite(sRaw) || !Number.isFinite(cRaw)) return null;
  // Clamp to [0,1] — score and ci are probabilities; out-of-range values are a
  // bug at the source but we don't want to advertise them to the user.
  const s = Math.max(0, Math.min(1, sRaw));
  const c = Math.max(0, Math.min(1, cRaw));
  return (
    <span className="text-[10px] font-semibold">
      {s.toFixed(2)} <span className={muted}>± {c.toFixed(2)}</span>
    </span>
  );
}
