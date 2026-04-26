import { motion } from "framer-motion";
import { Ambulance, ArrowRightLeft, FileText, Hospital, Stethoscope } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { getDoctorCopilotData, recommend } from "../lib/api";
import type { DoctorCopilotData, Hospital as HospitalType } from "../lib/types";

export default function DoctorCopilot() {
  const [data, setData] = useState<DoctorCopilotData | null>(null);
  const [hospitals, setHospitals] = useState<HospitalType[]>([]);
  const [sendingHospitalId, setSendingHospitalId] = useState<string>("");
  const [selectedReceivingId, setSelectedReceivingId] = useState<string>("");
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      setIsLoading(true);
      setErrorMessage(null);
      try {
        const [copilotData, hospitalResponse] = await Promise.all([
          getDoctorCopilotData(),
          recommend({ query: "Doctor copilot baseline hospitals" }),
        ]);
        setData(copilotData);
        setHospitals(hospitalResponse.hospitals);
        setSendingHospitalId(copilotData.sendingHospitalId);
        setSelectedReceivingId(copilotData.receivingHospitalIds[0] ?? "");
      } catch {
        setErrorMessage("Could not load doctor copilot data.");
      } finally {
        setIsLoading(false);
      }
    };

    void load();
  }, []);

  const receivingHospitals = useMemo(
    () =>
      hospitals.filter((hospital) => {
        if (!data) return false;
        return data.receivingHospitalIds.includes(hospital.id);
      }),
    [data, hospitals],
  );

  const sendingHospital = useMemo(
    () => hospitals.find((hospital) => hospital.id === sendingHospitalId),
    [hospitals, sendingHospitalId],
  );
  const activeReceiving = useMemo(
    () => receivingHospitals.find((hospital) => hospital.id === selectedReceivingId),
    [receivingHospitals, selectedReceivingId],
  );

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="space-y-4"
    >
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[1fr_1fr]">
        <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-5 shadow-premium">
          <div className="mb-4 inline-flex rounded-xl border border-indigo-500/40 bg-indigo-500/10 p-2.5 text-indigo-300">
            <Stethoscope size={18} />
          </div>
          <h2 className="text-xl font-semibold text-slate-100">Doctor Copilot</h2>
          <p className="mt-2 text-sm text-slate-400">
            Build and validate transfer referrals with destination readiness and rapid ETA guidance.
          </p>

          {errorMessage ? (
            <div className="mt-4 rounded-xl border border-rose-500/40 bg-rose-500/10 px-3 py-2 text-sm text-rose-200">
              {errorMessage}
            </div>
          ) : null}
          {isLoading ? (
            <div className="mt-4 rounded-xl border border-slate-800 bg-slate-950/70 px-3 py-2 text-sm text-slate-400">
              Loading hospital transfer context...
            </div>
          ) : null}

          <div className="mt-5 space-y-4">
            <label className="block">
              <div className="mb-2 text-xs uppercase tracking-widest text-slate-400">Sending hospital</div>
              <div className="relative">
                <Hospital className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" size={15} />
                <select
                  value={sendingHospitalId}
                  onChange={(e) => setSendingHospitalId(e.target.value)}
                  className="h-11 w-full rounded-xl border border-slate-700 bg-slate-950 pl-9 pr-3 text-sm text-slate-100 outline-none transition focus:border-indigo-500"
                >
                  {hospitals.map((hospital) => (
                    <option key={hospital.id} value={hospital.id}>
                      {hospital.name}
                    </option>
                  ))}
                </select>
              </div>
            </label>

            <div>
              <div className="mb-2 text-xs uppercase tracking-widest text-slate-400">Receiving hospitals</div>
              <div className="space-y-2">
                {!isLoading && receivingHospitals.length === 0 ? (
                  <div className="rounded-xl border border-dashed border-slate-700 px-3 py-2 text-sm text-slate-400">
                    No receiving hospitals available for this scenario.
                  </div>
                ) : null}
                {receivingHospitals.map((hospital) => (
                  <motion.button
                    whileHover={{ x: 2 }}
                    key={hospital.id}
                    type="button"
                    onClick={() => setSelectedReceivingId(hospital.id)}
                    className={`flex w-full items-center justify-between rounded-xl border px-3 py-2 text-left text-sm transition ${
                      selectedReceivingId === hospital.id
                        ? "border-emerald-500/60 bg-emerald-500/10 text-emerald-200"
                        : "border-slate-700 bg-slate-950 text-slate-300 hover:border-slate-600"
                    }`}
                  >
                    <span>{hospital.name}</span>
                    <span className="text-xs text-slate-400">{hospital.etaMinutes} min</span>
                  </motion.button>
                ))}
              </div>
            </div>
          </div>
        </div>

        <div className="space-y-4">
          <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-5 shadow-premium">
            <div className="mb-3 inline-flex rounded-xl border border-emerald-500/40 bg-emerald-500/10 p-2.5 text-emerald-300">
              <ArrowRightLeft size={18} />
            </div>
            <h3 className="text-base font-semibold text-slate-100">Referral preview</h3>
            <div className="mt-3 rounded-xl border border-slate-800 bg-slate-950/80 p-4">
              <div className="mb-2 text-xs text-slate-400">Route</div>
              <div className="text-sm text-slate-200">
                {sendingHospital?.name ?? "Loading"} <span className="text-slate-500">&rarr;</span>{" "}
                {activeReceiving?.name ?? "Loading"}
              </div>
              <div className="mt-3 flex flex-wrap gap-2">
                <span className="rounded-full border border-indigo-500/50 bg-indigo-500/10 px-2.5 py-1 text-xs text-indigo-200">
                  {data?.referralPreview.patientTag ?? "Loading..."}
                </span>
                <span className="rounded-full border border-rose-500/50 bg-rose-500/10 px-2.5 py-1 text-xs text-rose-200">
                  Priority: {data?.referralPreview.priority ?? "Pending"}
                </span>
              </div>
              <p className="mt-3 text-sm text-slate-400">{data?.referralPreview.notes ?? "Preparing referral note..."}</p>
            </div>
          </div>

          <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-5 shadow-premium">
            <div className="mb-3 inline-flex rounded-xl border border-emerald-500/40 bg-emerald-500/10 p-2.5 text-emerald-300">
              <Ambulance size={18} />
            </div>
            <h3 className="text-base font-semibold text-slate-100">Ambulance ETA</h3>
            <div className="mt-3 rounded-xl border border-slate-800 bg-slate-950/80 p-4">
              <div className="text-3xl font-semibold text-emerald-300">{data?.ambulanceEtaMinutes ?? "--"} min</div>
              <div className="mt-1 text-sm text-slate-400">Estimated arrival for transfer pickup</div>
            </div>
            <button
              type="button"
              disabled
              aria-disabled="true"
              title="Wired in Block 28 (reportlab via /transfer.referral_pdf_b64)"
              className="mt-4 inline-flex items-center gap-2 rounded-xl bg-indigo-500/40 px-3 py-2 text-xs font-semibold text-white/70 transition disabled:cursor-not-allowed"
            >
              <FileText size={14} />
              Generate referral PDF snapshot (coming soon)
            </button>
          </div>
        </div>
      </div>
    </motion.div>
  );
}
