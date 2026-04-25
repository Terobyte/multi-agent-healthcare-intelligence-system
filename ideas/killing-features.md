# Killing Features — Working List

Living doc. Seed it with everything we've discussed; trim ruthlessly later.

A "killing feature" here means: a single capability that, **on its own**, would make a family in Bihar / a doctor in a district hospital / an ASHA worker say *"I needed exactly this, today"*. If we can't say that out loud, it's not killing — it's a feature.

Ranking dims (apply to each candidate):
- **Pain killed** (1–5) — how acute is the moment we relieve
- **Demo-able in 24h** (1–5) — can we show it live to judges
- **Hard for others to copy** (1–5) — moat
- **Sponsor-fit (Databricks / data-heavy)** (1–5) — does it use the actual scale they care about

---

## Candidates

### 1. Voice-AI Hospital Pinger
**Scenario:** Family in rural UP wants to know if the district hospital has an ICU bed. Calling the front desk = 2 minutes of busy tone, then "ek minute" forever. Our agent calls in their place, in Hindi/Bhojpuri, asks one targeted question, hangs up in ~15 seconds, returns a structured answer.

**Why killing:** This is the **only path to "real-time" that respects the hospital staff**. It also removes the ghost-bed problem at the source — we ask only when a patient is actually about to travel.

**Open Q:** Is automated outbound voice to hospitals legally OK in India? Will small-hospital staff hang up on a robot? Can we make the bot polite enough that they cooperate?

---

### 2. Inter-Facility Transfer Copilot (the team's favorite)
**Scenario:** Doctor at a small hospital tells the family, "your mother's condition is worsening, take her to a tertiary care center." Today, the family scrambles: find a hospital that will accept her, get records transferred, hire an ambulance, hope she survives the ride. Our agent does this in one screen: ranks 3 receiving hospitals (by capability + availability + travel time), packages records (HL7 / FHIR / PDF), books an ambulance via 108 or private, opens a bridge channel between sending and receiving doctors.

**Why killing:** It's **the moment families lose people they shouldn't have lost**. Almost no software touches this end-to-end. Doctor-to-doctor is a B2B/operational sale; patient-side is the emotional one. We can pitch both.

**Open Q:** Can we get any read on 108 dispatch APIs? Can we fake ambulance booking convincingly in a demo?

---

### 3. Vernacular Triage via Voice + WhatsApp
**Scenario:** "Mere bachche ko bukhar hai, kuch nahi kha raha 2 din se." Mother types or speaks this in Hindi via WhatsApp. Our agent triages (red-flag symptoms? need ER? home care?) and either reassures or routes to the nearest right-tier facility with predicted availability and total cost.

**Why killing:** **Eliminates the "go to hospital just to find out it's the wrong hospital" failure mode**, which is the #1 source of catastrophic spend.

**Open Q:** What's the legal/clinical liability of an LLM doing triage? Do we frame it as "advisor, not diagnosis"? Sponsor-friendly disclaimer?

---

### 4. Predicted Bed-Availability Heatmap
**Scenario:** Map view; each hospital is a colored circle showing **predicted** ICU/general/maternity bed availability over the next 3 hours, fused from: historical occupancy patterns + most recent voice-verified ground-truth sample + crowdsourced "I just left this hospital" signals from patients we routed there yesterday.

**Why killing:** Solves "ghost bed" without lying. We don't claim live data — we claim **calibrated prediction with confidence bands**. Honest > fake-real-time.

**Open Q:** Where do we get the training history? Can we get hourly occupancy series from any state for ≥6 months? If not, we pre-train on synthetic + adapt.

---

### 5. Cost-Truth Advisor
**Scenario:** Every recommendation comes with **a cost preview that includes non-medical**: consult + meds + diagnostics (per common procedure) + travel (one-way + return for caregiver) + estimated 2 days lost wages. "This consult will cost ~₹2,400 medical + ~₹1,800 non-medical = ~₹4,200."

**Why killing:** **The 55M-into-poverty stat is mostly non-medical.** No competitor surfaces non-medical cost. This is also a wedge for govt/insurer partnerships later.

**Open Q:** How do we estimate non-medical cost honestly? Distance × ₹/km bus rate is doable; lost wages is rougher.

---

### 6. ASHA Co-Pilot
**Scenario:** ASHA worker opens a tablet/phone app. For each household visit she logs, the app: triages risk, generates a referral letter in vernacular and English, tracks the patient's onward journey, and pings her if the family didn't reach the recommended hospital within 24h.

**Why killing:** ASHAs are the **last-mile API into rural India**. Every country in the world that fixed rural health did it through frontline workers, not direct-to-patient apps.

**Open Q:** What devices/network do real ASHAs have? Are there policy hurdles to a private app supplementing ASHA Soft?

---

### 7. SMS / IVR Fallback Channel
**Scenario:** No internet, no smartphone. SMS "BUKHAR 800100" to a number; receive back: "Nearest open clinic: PHC Sitapur, 4km, open till 8pm. Reply 1 for directions." Or call an IVR number, speak the symptom, hear back the routing.

**Why killing:** **The people who need this most don't have data**. A web/app demo loses this entire population. SMS+IVR shows we actually understand the user.

**Open Q:** Twilio India? Local SMS gateway? Can we buy a shortcode for the demo?

---

### 8. Bridge Doctor Mode (B2D2)
**Scenario:** Two doctors on a transfer call have a live shared screen with patient summary, vitals, current meds, allergies, ECG image — auto-built from the sending hospital's records (even if it's a paper chart photographed and OCR'd). The receiving doctor accepts/rejects with one tap.

**Why killing:** Today this happens via WhatsApp at 2am. Replacing WhatsApp with a structured handoff is a **clinical win**, not a UX win.

**Open Q:** Can we OCR Indian-handwriting medical notes well enough for a demo? Do we lean on dummy data?

---

## Discussion Prompts

- **Which 2–3 do we put on the demo path?** (everything else is "future work" slide)
- **Which one do we lead the pitch with?** (the headline determines the brand)
- **What's missing from this list?** (especially anything Databricks-specific — geospatial scale, Lakehouse, MLflow)

---

## Killed / Deprioritized

(move things here as we cut them — keeps the rationale visible)

- *(none yet)*
