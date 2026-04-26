export default function ConfidenceInterval({ score, ci }: { score: number; ci: number }) {
  return (
    <span className="text-[11px] text-slate-400">
      {Math.round(score * 100)}% <span className="text-slate-500">+/- {Math.round(ci * 100)}%</span>
    </span>
  );
}
