import { motion } from "framer-motion";

export type BookingState = "idle" | "reserving" | "success" | "rollback";

const tileLabels = ["Bed", "Oxygen", "Drug", "Specialist"];

const stateClass = {
  success: "border-[rgba(74,107,63,0.40)] bg-[rgba(74,107,63,0.20)] text-cg-sage",
  rollback: "border-[rgba(194,82,43,0.40)] bg-[rgba(194,82,43,0.20)] text-cg-peach",
  idle: "border-white/[0.06] bg-[rgba(40,40,42,0.7)] text-cg-mist5",
  reserving: "border-white/[0.06] bg-[rgba(40,40,42,0.7)] text-cg-mist5",
} as const;

interface AtomicBookingTilesProps {
  state: BookingState;
  // Optional: surfaced from the booking saga when a leg fails. Falls back to a
  // generic message so the rollback flip never lands silently — color alone
  // does not satisfy "tell the user what went wrong" UX.
  errorMessage?: string;
}

export default function AtomicBookingTiles({
  state,
  errorMessage = "Reservation could not complete",
}: AtomicBookingTilesProps) {
  return (
    <div className="rounded-cg-card border border-white/[0.05] bg-[rgba(35,35,36,0.85)] p-4 backdrop-blur-cg-glass">
      <div className="mb-3 text-sm font-semibold text-cg-ivory">Atomic booking state</div>
      <div className="grid grid-cols-2 gap-2">
        {tileLabels.map((tile, index) => (
          <motion.div
            key={tile}
            className={`rounded-cg-tile border px-3 py-3 text-center text-xs font-semibold transition ${stateClass[state]}`}
            animate={{
              rotateX: state === "success" || state === "rollback" ? [0, 90, 0] : 0,
              scale: state === "reserving" ? [1, 1.02, 1] : 1,
            }}
            transition={{
              duration: 0.35,
              delay: state === "success" ? index * 0.08 : 0,
              repeat: state === "reserving" ? Infinity : 0,
              repeatDelay: 0.5,
            }}
          >
            {tile}
          </motion.div>
        ))}
      </div>
      {state === "rollback" ? (
        <div
          role="alert"
          className="mt-3 rounded-cg-tile border border-[rgba(194,82,43,0.40)] bg-[rgba(194,82,43,0.12)] px-3 py-2 text-xs text-cg-peach"
        >
          Reservation rolled back: {errorMessage}
        </div>
      ) : null}
    </div>
  );
}
