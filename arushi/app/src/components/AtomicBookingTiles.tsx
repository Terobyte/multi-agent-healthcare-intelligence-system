import { motion } from "framer-motion";

export type BookingState = "idle" | "reserving" | "success" | "rollback";

const tileLabels = ["Bed", "Oxygen", "Drug", "Specialist"];

export default function AtomicBookingTiles({ state }: { state: BookingState }) {
  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4 shadow-premium">
      <div className="mb-3 text-sm font-semibold text-slate-100">Atomic booking state</div>
      <div className="grid grid-cols-2 gap-2">
        {tileLabels.map((tile, index) => {
          const isGreen = state === "success";
          const isRed = state === "rollback";
          return (
            <motion.div
              key={tile}
              className={`rounded-xl border px-3 py-3 text-center text-xs font-medium ${
                isGreen
                  ? "border-emerald-500/70 bg-emerald-500/20 text-emerald-200"
                  : isRed
                    ? "border-rose-500/80 bg-rose-500/20 text-rose-200"
                    : "border-slate-700 bg-slate-950 text-slate-300"
              }`}
              animate={{
                rotateX: isGreen || isRed ? [0, 90, 0] : 0,
                scale: state === "reserving" ? [1, 1.02, 1] : 1,
              }}
              transition={{
                duration: 0.35,
                delay: isGreen ? index * 0.08 : 0,
                repeat: state === "reserving" ? Infinity : 0,
                repeatDelay: 0.5,
              }}
            >
              {tile}
            </motion.div>
          );
        })}
      </div>
    </div>
  );
}
