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
  { key: "patient", label: "Patient Flow", icon: ActivitySquare },
  { key: "doctor", label: "Doctor Copilot", icon: Bot },
  { key: "ngo", label: "NGO Dashboard", icon: Landmark },
];

export default function App() {
  const [activeTab, setActiveTab] = useState<TabKey>("patient");
  const ActivePage = useMemo(() => {
    if (activeTab === "doctor") return DoctorCopilot;
    if (activeTab === "ngo") return NGODashboard;
    return PatientFlow;
  }, [activeTab]);

  return (
    <div className="min-h-screen bg-slate-950 bg-hero-radial text-slate-100">
      <div className="mx-auto max-w-7xl px-6 py-8">
        <header className="mb-6 flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-xs uppercase tracking-[0.24em] text-indigo-300">Hackathon demo</p>
            <h1 className="mt-1 text-3xl font-semibold tracking-tight">Healthcare Intelligence</h1>
          </div>
          <div className="rounded-xl border border-slate-800 bg-slate-900/70 px-3 py-2 text-xs text-slate-300">
            AI triage + trust signals + live routing
          </div>
        </header>

        <div className="mb-6 inline-flex rounded-2xl border border-slate-800 bg-slate-900/75 p-1">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            const active = activeTab === tab.key;
            return (
              <button
                key={tab.key}
                type="button"
                className={`relative flex items-center gap-2 rounded-xl px-4 py-2 text-sm transition ${
                  active ? "text-white" : "text-slate-400 hover:text-slate-200"
                }`}
                onClick={() => setActiveTab(tab.key)}
              >
                {active && (
                  <motion.span
                    layoutId="tab-pill"
                    className="absolute inset-0 rounded-xl bg-indigo-500/30"
                    transition={{ type: "spring", stiffness: 380, damping: 28 }}
                  />
                )}
                <Icon size={15} className="relative z-10" />
                <span className="relative z-10">{tab.label}</span>
              </button>
            );
          })}
        </div>

        <AnimatePresence mode="sync">
          <motion.div
            key={activeTab}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.22 }}
          >
            <ActivePage />
          </motion.div>
        </AnimatePresence>
      </div>
    </div>
  );
}
