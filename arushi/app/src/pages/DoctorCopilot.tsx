import { motion } from "framer-motion";
import { Ambulance, ArrowRightLeft, FileText, Hospital, RefreshCw, Stethoscope } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { getDoctorCopilotData, recommend } from "../lib/api";
import type { DoctorCopilotData, Hospital as HospitalType } from "../lib/types";

export default function DoctorCopilot() {
  const [data, setData] = useState<DoctorCopilotData | null>(null);
  const [hospitals, setHospitals] = useState<HospitalType[]>([]);
  const [sendingHospitalId, setSendingHospitalId] = useState<string>("");
  const [selectedReceivingId, setSelectedReceivingId] = useState<string>("");
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [bothFailed, setBothFailed] = useState(false);

  const load = useCallback(async (signal?: { active: boolean }) => {
    setIsLoading(true);
    setErrorMessage(null);
    setBothFailed(false);
    const [copilotResult, hospitalResult] = await Promise.allSettled([
      getDoctorCopilotData(),
      recommend({ query: "Doctor copilot baseline hospitals" }),
    ]);
    // Guard against tab-switch / unmount during the await — without this
    // the setState calls would leak warnings in dev StrictMode.
    if (signal && !signal.active) return;

    let nextData: DoctorCopilotData | null = null;
    let nextHospitals: HospitalType[] = [];

    if (copilotResult.status === "fulfilled") {
      nextData = copilotResult.value;
      setData(copilotResult.value);
    }
    if (hospitalResult.status === "fulfilled") {
      nextHospitals = hospitalResult.value.hospitals;
      setHospitals(hospitalResult.value.hospitals);
    }

    // Reconcile sending hospital: if copilot returned an ID that's not in the
    // hospital list, fall back to first available so the <select> isn't orphan.
    if (nextHospitals.length > 0) {
      const candidateId = nextData?.sendingHospitalId ?? "";
      const idsInList = nextHospitals.map((h) => h.id);
      if (candidateId && idsInList.includes(candidateId)) {
        setSendingHospitalId(candidateId);
      } else {
        setSendingHospitalId(nextHospitals[0]?.id ?? "");
      }
    } else {
      setSendingHospitalId("");
    }

    if (nextData) {
      setSelectedReceivingId(nextData.receivingHospitalIds[0] ?? "");
    }

    const failures: string[] = [];
    if (copilotResult.status === "rejected") failures.push("copilot context");
    if (hospitalResult.status === "rejected") failures.push("hospital list");
    if (failures.length > 0) {
      setErrorMessage(`Could not load: ${failures.join(", ")}. Showing partial data.`);
    }
    setBothFailed(failures.length === 2);
    setIsLoading(false);
  }, []);

  useEffect(() => {
    const signal = { active: true };
    void load(signal);
    return () => {
      signal.active = false;
    };
  }, [load]);

  // If the data payload changes (e.g. retry/reload returns new ordering), make
  // sure the currently-selected receiving hospital still exists in the list.
  useEffect(() => {
    if (!data) return;
    if (data.receivingHospitalIds.length === 0) {
      if (selectedReceivingId !== "") setSelectedReceivingId("");
      return;
    }
    if (!data.receivingHospitalIds.includes(selectedReceivingId)) {
      setSelectedReceivingId(data.receivingHospitalIds[0] ?? "");
    }
  }, [data, selectedReceivingId]);

  // Guard: if the user changed sendingHospitalId via select but a backend
  // refresh removed that hospital, snap back to the first available option.
  useEffect(() => {
    if (hospitals.length === 0) return;
    const ids = hospitals.map((h) => h.id);
    if (sendingHospitalId && !ids.includes(sendingHospitalId)) {
      setSendingHospitalId(hospitals[0]?.id ?? "");
    }
  }, [hospitals, sendingHospitalId]);

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
        <div className="rounded-cg-card border border-white/[0.05] bg-[rgba(35,35,36,0.85)] p-5 backdrop-blur-cg-glass">
          <div className="mb-4 inline-flex rounded-xl border border-[rgba(135,168,120,0.30)] bg-[rgba(135,168,120,0.15)] p-2.5 text-cg-sage">
            <Stethoscope size={18} />
          </div>
          <h2 className="text-xl font-semibold tracking-cg-tight text-cg-ivory">Doctor Copilot</h2>
          <p className="mt-2 text-sm text-cg-mist2">
            Build and validate transfer referrals with destination readiness and rapid ETA guidance.
          </p>

          {errorMessage ? (
            <div className="mt-4 flex items-start justify-between gap-3 rounded-cg-tile border border-[rgba(194,82,43,0.40)] bg-[rgba(194,82,43,0.15)] px-3 py-2 text-sm text-cg-peach">
              <span>{errorMessage}</span>
              {bothFailed ? (
                <button
                  type="button"
                  onClick={() => void load()}
                  className="inline-flex shrink-0 items-center gap-1.5 rounded-lg border border-[rgba(255,176,136,0.40)] bg-[rgba(255,176,136,0.20)] px-2.5 py-1 text-xs font-semibold text-cg-peach transition hover:bg-[rgba(255,176,136,0.28)]"
                >
                  <RefreshCw size={12} />
                  Retry
                </button>
              ) : null}
            </div>
          ) : null}
          {isLoading ? (
            <div className="mt-4 rounded-cg-tile border border-white/[0.05] bg-[rgba(20,20,21,0.7)] px-3 py-2 text-sm text-cg-mist2">
              Loading hospital transfer context...
            </div>
          ) : null}

          <div className="mt-5 space-y-4">
            <label className="block">
              <div className="mb-2 text-xs uppercase tracking-cg-overline text-cg-mist4">Sending hospital</div>
              <div className="relative">
                <Hospital className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-cg-mist3" size={15} />
                <select
                  value={sendingHospitalId}
                  onChange={(e) => setSendingHospitalId(e.target.value)}
                  className="h-11 w-full rounded-xl border border-white/[0.08] bg-[rgba(20,20,21,0.7)] pl-9 pr-3 text-sm text-cg-ivory outline-none transition focus:border-cg-sage"
                >
                  {hospitals.length === 0 ? (
                    <option value="" disabled>
                      {isLoading ? "Loading hospitals..." : "No hospitals available"}
                    </option>
                  ) : null}
                  {hospitals.map((hospital) => (
                    <option key={hospital.id} value={hospital.id}>
                      {hospital.name}
                    </option>
                  ))}
                </select>
              </div>
            </label>

            <div>
              <div className="mb-2 text-xs uppercase tracking-cg-overline text-cg-mist4">Receiving hospitals</div>
              <div className="space-y-2">
                {!isLoading && receivingHospitals.length === 0 ? (
                  <div className="rounded-cg-tile border border-dashed border-white/[0.10] px-3 py-2 text-sm text-cg-mist3">
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
                        ? "border-[rgba(135,168,120,0.40)] bg-[rgba(135,168,120,0.15)] text-cg-sage"
                        : "border-white/[0.08] bg-[rgba(20,20,21,0.6)] text-cg-mist1 hover:border-white/[0.16]"
                    }`}
                  >
                    <span>{hospital.name}</span>
                    <span className="text-xs text-cg-mist3">{hospital.etaMinutes} min</span>
                  </motion.button>
                ))}
              </div>
            </div>
          </div>
        </div>

        <div className="space-y-4">
          <div className="rounded-cg-card border border-white/[0.05] bg-[rgba(35,35,36,0.85)] p-5 backdrop-blur-cg-glass">
            <div className="mb-3 inline-flex rounded-xl border border-[rgba(135,168,120,0.30)] bg-[rgba(135,168,120,0.15)] p-2.5 text-cg-sage">
              <ArrowRightLeft size={18} />
            </div>
            <h3 className="text-base font-semibold tracking-[-0.01em] text-cg-ivory">Referral preview</h3>
            <div className="mt-3 rounded-cg-tile border border-white/[0.05] bg-[rgba(20,20,21,0.7)] p-4">
              <div className="mb-2 text-xs text-cg-mist3">Route</div>
              <div className="text-sm text-cg-mist5">
                {sendingHospital?.name ?? (isLoading ? "Loading…" : "Unknown sending hospital")}{" "}
                <span className="text-cg-mist4">&rarr;</span>{" "}
                {activeReceiving?.name ?? (isLoading ? "Loading…" : "Select a receiving hospital")}
              </div>
              <div className="mt-3 flex flex-wrap gap-2">
                <span className="rounded-full border border-[rgba(135,168,120,0.30)] bg-[rgba(135,168,120,0.15)] px-2.5 py-1 text-xs font-semibold text-cg-sage">
                  {data?.referralPreview.patientTag ?? "Loading..."}
                </span>
                <span className="rounded-full border border-[rgba(255,176,136,0.30)] bg-[rgba(255,176,136,0.15)] px-2.5 py-1 text-xs font-semibold text-cg-peach">
                  Priority: {data?.referralPreview.priority ?? "Pending"}
                </span>
              </div>
              <p className="mt-3 text-sm text-cg-mist2">{data?.referralPreview.notes ?? "Preparing referral note..."}</p>
            </div>
          </div>

          <div className="rounded-cg-card border border-white/[0.05] bg-[rgba(35,35,36,0.85)] p-5 backdrop-blur-cg-glass">
            <div className="mb-3 inline-flex rounded-xl border border-[rgba(135,168,120,0.30)] bg-[rgba(135,168,120,0.15)] p-2.5 text-cg-sage">
              <Ambulance size={18} />
            </div>
            <h3 className="text-base font-semibold tracking-[-0.01em] text-cg-ivory">Ambulance ETA</h3>
            <div className="mt-3 rounded-cg-tile border border-white/[0.05] bg-[rgba(20,20,21,0.7)] p-4">
              <div className="text-3xl font-bold tracking-cg-num text-cg-sage">{data?.ambulanceEtaMinutes ?? "--"} min</div>
              <div className="mt-1 text-sm text-cg-mist2">Estimated arrival for transfer pickup</div>
            </div>
            <button
              type="button"
              disabled
              aria-disabled="true"
              title="Wired in Block 28 (reportlab via /transfer.referral_pdf_b64)"
              className="mt-4 inline-flex items-center gap-2 rounded-xl bg-[rgba(135,168,120,0.20)] px-3 py-2 text-xs font-semibold text-cg-sage/80 transition disabled:cursor-not-allowed"
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
