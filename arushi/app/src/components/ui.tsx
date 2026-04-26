import type { ReactNode } from "react";

export function GlassCard({ children, className = "" }: { children: ReactNode; className?: string }) {
  return (
    <div
      className={`rounded-2xl border border-slate-800/90 bg-slate-900/70 p-4 shadow-premium backdrop-blur-sm ${className}`}
    >
      {children}
    </div>
  );
}
