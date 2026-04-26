import { motion } from "framer-motion";

export type BookingState = "idle" | "reserving" | "success" | "rollback";

type TileState = "neutral" | "committed" | "failed";

interface TileSpec {
  name: string;
  state: TileState;
  value: string;
}

function tilesFor(state: BookingState): TileSpec[] {
  if (state === "success") {
    return [
      { name: "Bed", state: "committed", value: "✓ 4B-12" },
      { name: "Oxygen", state: "committed", value: "✓ 8L" },
      { name: "Drug", state: "committed", value: "✓ Asp." },
      { name: "Specialist", state: "committed", value: "✓ on-shift" },
    ];
  }
  if (state === "rollback") {
    return [
      { name: "Bed", state: "committed", value: "✓ 4B-12" },
      { name: "Oxygen", state: "committed", value: "✓ 8L" },
      { name: "Drug", state: "committed", value: "✓ Asp." },
      { name: "Specialist", state: "failed", value: "↺ retry" },
    ];
  }
  if (state === "reserving") {
    return [
      { name: "Bed", state: "neutral", value: "…" },
      { name: "Oxygen", state: "neutral", value: "…" },
      { name: "Drug", state: "neutral", value: "…" },
      { name: "Specialist", state: "neutral", value: "…" },
    ];
  }
  return [
    { name: "Bed", state: "neutral", value: "—" },
    { name: "Oxygen", state: "neutral", value: "—" },
    { name: "Drug", state: "neutral", value: "—" },
    { name: "Specialist", state: "neutral", value: "—" },
  ];
}

function headerFor(state: BookingState): { h3: string; foot: string } {
  if (state === "success") return { h3: "4 of 4 committed", foot: "All resources locked. Reservation confirmed." };
  if (state === "rollback")
    return {
      h3: "3 of 4 committed",
      foot: "Cardiologist roster mid-rotation — retrying specialist slot.",
    };
  if (state === "reserving") return { h3: "Reserving across 4 resources", foot: "Locking bed, oxygen, drug, specialist…" };
  return { h3: "Idle", foot: "Send a query to start an atomic reservation." };
}

const tileBaseClass =
  "flex min-w-0 flex-col items-center justify-center overflow-hidden rounded-cg-tile border px-2 py-3 text-center transition";

const tileStateClass: Record<TileState, string> = {
  neutral: "border-white/[0.06] bg-[rgba(40,40,42,0.7)]",
  committed: "border-[rgba(74,107,63,0.40)] bg-[rgba(74,107,63,0.20)]",
  failed: "border-[rgba(194,82,43,0.40)] bg-[rgba(194,82,43,0.20)]",
};

const valueColorByState: Record<TileState, string> = {
  neutral: "text-cg-ivory",
  committed: "text-cg-sage",
  failed: "text-cg-peach",
};

export default function AtomicBookingTiles({ state }: { state: BookingState }) {
  const tiles = tilesFor(state);
  const header = headerFor(state);
  return (
    <div className="rounded-cg-card border border-white/[0.05] bg-[rgba(35,35,36,0.85)] p-4 backdrop-blur-cg-glass">
      <div className="text-[10px] font-semibold uppercase tracking-cg-overline text-cg-mist4">
        Atomic booking · live
      </div>
      <h3 className="mt-1.5 text-[16px] font-semibold tracking-[-0.01em] text-cg-ivory">
        {header.h3}
      </h3>
      <div className="mt-3 grid grid-cols-4 gap-2">
        {tiles.map((tile, index) => (
          <motion.div
            key={tile.name}
            className={`${tileBaseClass} ${tileStateClass[tile.state]}`}
            animate={{
              scale: state === "reserving" ? [1, 1.02, 1] : 1,
            }}
            transition={{
              duration: 0.6,
              delay: state === "success" || state === "rollback" ? index * 0.08 : 0,
              repeat: state === "reserving" ? Infinity : 0,
              repeatDelay: 0.4,
            }}
          >
            <div className="w-full overflow-hidden truncate text-[9px] font-semibold uppercase tracking-[0.08em] text-cg-mist4">
              {tile.name}
            </div>
            <div
              className={`mt-1 w-full overflow-hidden truncate text-[14px] font-bold tracking-[-0.02em] ${valueColorByState[tile.state]}`}
            >
              {tile.value}
            </div>
          </motion.div>
        ))}
      </div>
      <div className="mt-2.5 text-[11px] text-cg-mist3">{header.foot}</div>
    </div>
  );
}
