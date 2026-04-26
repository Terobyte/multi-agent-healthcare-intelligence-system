import { AnimatePresence, motion } from "framer-motion";
import { ActivitySquare, Bot, Landmark, type LucideIcon } from "lucide-react";
import { useMemo, useState } from "react";
import DoctorCopilot from "./pages/DoctorCopilot";
import NGODashboard from "./pages/NGODashboard";
import PatientFlow from "./pages/PatientFlow";

type TabKey = "patient" | "doctor" | "ngo";

const tabs: {
  key: TabKey;
  label: string;
  icon: LucideIcon;
}[] = [
  { key: "patient", label: "Patient", icon: ActivitySquare },
  { key: "doctor", label: "Doctor", icon: Bot },
  { key: "ngo", label: "NGO", icon: Landmark },
];

export default function App() {
  const [activeTab, setActiveTab] = useState<TabKey>("patient");
  const ActivePage = useMemo(() => {
    if (activeTab === "doctor") return DoctorCopilot;
    if (activeTab === "ngo") return NGODashboard;
    return PatientFlow;
  }, [activeTab]);

  return (
    <div className="min-h-screen bg-cg-page text-cg-ivory">
      <div className="mx-auto max-w-[1304px] px-6 pb-10 pt-6">
        <div className="mb-4 flex items-center justify-between gap-3">
          <div className="flex items-center gap-2.5">
            <div className="h-7 w-7 rounded-lg bg-cg-grad-logo-peach" />
            <span className="text-[15px] font-semibold tracking-cg-tight text-cg-ivory">
              CareGuide
            </span>
            <span className="ml-2 text-[11px] uppercase tracking-cg-overline-wide text-cg-mist4">
              Hackathon demo
            </span>
          </div>
          <div className="inline-flex rounded-full border border-white/[0.06] bg-cg-stage/70 p-1 backdrop-blur-cg-glass">
            {tabs.map((tab) => {
              const Icon = tab.icon;
              const active = activeTab === tab.key;
              return (
                <button
                  key={tab.key}
                  type="button"
                  className={`relative flex items-center gap-2 rounded-full px-3.5 py-1.5 text-xs font-semibold transition ${
                    active ? "text-cg-peach-ink" : "text-cg-mist2 hover:text-cg-mist5"
                  }`}
                  onClick={() => setActiveTab(tab.key)}
                >
                  {active && (
                    <motion.span
                      layoutId="cg-tab-pill"
                      className="absolute inset-0 rounded-full bg-cg-peach"
                      transition={{ type: "spring", stiffness: 380, damping: 28 }}
                    />
                  )}
                  <Icon size={14} className="relative z-10" />
                  <span className="relative z-10">{tab.label}</span>
                </button>
              );
            })}
          </div>
        </div>

        <AnimatePresence mode="wait">
          <motion.div
            key={activeTab}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -6 }}
            transition={{ duration: 0.22 }}
          >
            <ActivePage />
          </motion.div>
        </AnimatePresence>
      </div>
    </div>
  );
}
