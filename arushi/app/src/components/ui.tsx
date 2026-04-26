import type { ReactNode } from "react";

export function GlassCard({ children, className = "" }: { children: ReactNode; className?: string }) {
  return (
    <div
      className={`rounded-cg-card border border-white/[0.05] bg-[rgba(35,35,36,0.85)] p-4 backdrop-blur-cg-glass ${className}`}
    >
      {children}
    </div>
  );
}
