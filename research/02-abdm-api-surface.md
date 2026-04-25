# 02 — ABDM API Surface (What's Actually Reachable in 24h)

## TL;DR

1. **Sandbox is open in 30 seconds** — register an email, get `clientId`/`clientSecret`, hit V3 APIs immediately. No facility, no audit, no certification. This is the only ABDM surface a hackathon can use.
2. **Production is gated by CERT-IN audit + QCI certification** — M2 (sharing clinical data) and M3 (consuming it) need FHIR R4 mapping, Fidelius ECDH+AES-256-GCM crypto, and a security audit. **Minimum 2–8 weeks**. Not in scope for 24h.
3. **The viable hackathon path is EUA on UHI/Beckn + ABHA creation (M1)** — build a patient-facing app that searches a decentralized network of hospital HSPAs via `search → select → init → confirm`. Skips FHIR, skips Fidelius, skips empanelment.

> **★ INSIGHT (Killing Feature B)** — The Beckn `search → on_search` choreography is *exactly* the multi-receiving-hospital ranking flow our Transfer Copilot needs. We can demo a "find a receiving ICU" call by stubbing 2–3 HSPAs that respond with availability + price, with the supervisor agent narrating the choice. No real ABDM production access required.

---

## What's Reachable Without Empanelment

| Surface | Open in sandbox? | Hackathon viable? | Why |
|---|---|---|---|
| OAuth gateway sessions (V3) | Yes | Yes | Email signup → JWT |
| ABHA creation (Aadhaar OTP, simulated) | Yes | Yes | M1 identity |
| HFR facility lookup (read) | Yes | Yes | Hospital geocode/registry |
| HPR practitioner lookup | Yes | Yes | Doctor verification UI |
| UHI Beckn search/select/init/confirm | Yes | **Yes — primary path** | No clinical data, fully open |
| M2 HIP (push clinical bundles) | Sandbox only | No | Needs FHIR + Fidelius + CERT-IN |
| M3 HIU (pull clinical bundles) | Sandbox only | No | Needs decryption + QCI cert |
| AB-PMJAY claims (M4) | Production only | No | Empanelment required |

---

## Auth: V3 Gateway

| Env | Base URL | Session endpoint (POST) |
|---|---|---|
| Sandbox | `https://dev.abdm.gov.in` | `/api/hiecm/gateway/v3/sessions` |
| Prod | `https://apis.abdm.gov.in` | `/api/hiecm/gateway/v3/sessions` |

```json
{
  "clientId": "SBX_000135",
  "clientSecret": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "grantType": "client_credentials"
}
```

Returns JWT (`accessToken`, `expiresIn` ~1200s, `refreshToken`).

**Required headers on every call:**
- `Authorization: Bearer <jwt>`
- `REQUEST-ID`: UUID v4 per call
- `TIMESTAMP`: ISO 8601 UTC `YYYY-MM-DD'T'HH:MM:SS.SSS'Z'`
- `X-CM-ID`: `sbx` (sandbox) or `abdm` (prod)

**Rate limits:** sandbox 25 RPM, prod 500 RPM baseline, enterprise up to 5M calls/24h. 429s → exponential backoff.

> **★ INSIGHT** — Sandbox 25 RPM is the binding constraint for a live demo. Cache aggressively; one judge clicking "search" five times in 30s will burn the budget. Pre-warm calls during dev.

---

## Crypto Mandate (Sensitive Fields Only)

Aadhaar, mobile, OTP, password **must** be RSA-encrypted *before* HTTP transmission. Cipher: `RSA/ECB/OAEPWithSHA-1AndMGF1Padding`.

Public key fetched from `GET /v3/profile/public/certificate` (rotates — poll periodically).

TLS 1.2+ alone is not enough. Plaintext sensitive fields → instant API rejection.

---

## ABHA Enrollment (M1 — what we'll demo)

**Step 1 — request OTP:**
```json
POST /v3/enrollment/request/otp
{
  "txnId": "",
  "scope": ["abha-enrol"],
  "loginHint": "aadhaar",
  "loginId": "<RSA-encrypted-aadhaar>",
  "otpSystem": "aadhaar"
}
```

**Step 2 — enrol with OTP:**
```json
POST /v3/enrollment/enrol/byAadhaar
{
  "txnId": "<from-step-1>",
  "scope": ["abha-enrol"],
  "authData": {
    "authMethods": ["otp"],
    "otp": {
      "txnId": "<from-step-1>",
      "otpValue": "<RSA-encrypted-otp>",
      "mobile": "<RSA-encrypted-mobile>"
    }
  },
  "consent": { "code": "abha-enrollment", "version": "1.4" }
}
```

Alt paths: `byDocument` (driving license, base64 photos), face/fingerprint PID blocks.

**V3 Scan & Share:** patient scans facility QR → `/v3/hip/patient/profile/share` POSTs profile + a long-lived linking token to the HIS. Token persists, so future records auto-link without OTPs.

> **★ INSIGHT (Killing Feature A)** — Scan & Share is the cleanest "real ABDM signal" we can show in the patient UI: scan QR at hospital, ABHA profile pre-fills the triage form, future visits auto-link. ~5 lines of JS handling on the frontend.

---

## HFR (Health Facility Registry)

| Env | Web | Swagger |
|---|---|---|
| Sandbox | `https://hspsbx.abdm.gov.in/home` | `https://facilitysbx.abdm.gov.in/swagger-ui.html` |
| Prod | `https://nhpr.abdm.gov.in/home` | `https://facility.abdm.gov.in/swagger-ui.html` |

Facility ID format: 12 chars, prefix `IN`. E.g. `IN0710001283`.

**Levenshtein dedup:** create-facility runs name comparison vs existing entries in same state/district/PIN. Distance < 4 → API rejects with disambiguation error. Cuts duplicate facility sprawl.

**Bridge URL binding (multi-tenant SaaS pattern):**
```json
POST /v1/bridges/MutipleHRPAddUpdateServices
{
  "facilityId": "IN0710001283",
  "facilityName": "S Y Hospital New Delhi",
  "HRP": "SBX_TEST_SC"
}
```

One bridge URL handles many facilities — middleware inspects `hip.id` in incoming payloads to route to the right tenant.

> **★ INSIGHT** — HFR has the registry data we want for the 10k hospital ingest, but only as identity (name, location, ownership). **No bed counts, no occupancy.** Use HFR as the geocoding/dedup baseline; bed data has to come from elsewhere (synthetic or partner hospital).

---

## HPR (Healthcare Professionals Registry)

14-digit practitioner ID. Pull master lists for dropdowns (medical councils, courses, universities) via:

```json
POST https://hpr.abdm.gov.in/apis/v1/masters/courses
{ "systemOfMedicine": 1, "hprType": "doctor", "name": "mbbs" }
```

Useful only for credential-validation UI in the doctor-side Transfer Copilot screen.

---

## M1 / M2 / M3 — What Each Tier Costs

| Tier | Role | What it does | Hackathon? |
|---|---|---|---|
| **M1** | Identity Provider | ABHA create, demographic verify, Scan & Share, patient discovery | **Yes** — sandbox |
| **M2** | HIP (Health Information Provider) | Push FHIR R4 bundles (Prescription, DiagnosticReport, OPConsultNote, DischargeSummary, etc.) on consent | No — needs FHIR mapping + Fidelius |
| **M3** | HIU (Health Information User) | Pull and decrypt remote clinical bundles | No — needs decryption + QCI cert |

**M2 hard parts:**
- FHIR R4 bundle construction per NRCeS profiles
- Local terminology → SNOMED-CT / ICD-10 mapping
- **Fidelius crypto:** ECDH key exchange → AES-256-GCM, ephemeral keypair per transaction, nonce, encrypted blob to data-push URL
- Async event handling: must HTTP 202 instantly, push real work to background worker
- Multi-system orchestration when HIS / LIMS / RIS each speak different formats

**M3 hard parts:** inverse Fidelius decrypt, normalizing FHIR variations across vendors, no polluting local DB with unverified external records.

> **★ INSIGHT (Killing Feature B)** — When the Transfer Copilot says "we package the patient record in FHIR and push it to the receiving hospital," that's M2 — and we can't really do it. **Fake it as a structured PDF + JSON snippet for the demo**, with a note that "production requires CERT-IN audit + Fidelius pipeline." Judges will accept this; nobody builds Fidelius in a hackathon.

---

## UHI / Beckn — The Hackathon Sweet Spot

**EUA** = consumer app (us). **HSPA** = hospital backend. UHI Gateway routes between them. No prior bilateral contract needed — Beckn protocol JSON is the contract.

**Lifecycle:** `search → on_search → select → on_select → init → on_init → confirm → on_confirm`

Search payload (broadcast to every HSPA in domain):
```json
{
  "context": {
    "domain": "nic2004:85195",
    "country": "IND",
    "city": "std:080",
    "action": "search",
    "core_version": "0.9.3",
    "bap_id": "api.eua-provider.com",
    "bap_uri": "https://api.eua-provider.com/uhi/v1"
  },
  "message": {
    "intent": {
      "provider": { "category_id": "pediatrics" },
      "fulfillment": {
        "type": "teleconsultation",
        "start": { "time": { "timestamp": "2026-05-10T10:00:00Z" } }
      }
    }
  }
}
```

`on_search` returns aggregated catalogs (provider profiles via HPR, slots, prices). `select` is point-to-point to a single HSPA — locks slot + returns quote. `init` transfers patient details + final billing. `confirm` commits the appointment.

Aux APIs: `status`, `update`, `cancel`, `rating`.

> **★ INSIGHT (Killing Feature B)** — `category_id: "pediatrics"` becomes our hospital-capability dimension. We can stub 3 HSPAs (district / urban / tertiary) responding with `{availability, price, distance}` and let the supervisor agent rank them. This *is* the demo for "we found you a receiving hospital."

---

## Production Pathway (For Reference Only)

Sandbox → prod requires:
- VAPT by CERT-IN-empanelled vendor
- AES-256 encryption at rest
- OAuth 2.0 robustness validation
- Webhook injection-attack hardening
- QCI certification (verifies ABHA capture, FHIR R4 validity, Fidelius correctness)

Then NHA provisions production keys. Not relevant for 24h.

---

## 24-Hour Build Plan (ABDM-Adjacent)

In sandbox we can:
1. ✅ OAuth via `client_credentials`
2. ✅ Create ABHA (Aadhaar OTP simulated)
3. ✅ HFR facility lookup → 10k hospital geocode/normalization
4. ✅ HPR practitioner stub for doctor profile cards
5. ✅ Beckn `search/select/init/confirm` between EUA and 2–3 mock HSPAs

Skip:
- ✗ Real M2 FHIR pushes (mock as PDF + JSON)
- ✗ Fidelius crypto (handwave in slide)
- ✗ HFR write APIs (read only, no facility creation)
- ✗ Production keys

---

## Sources

- ABDM dev portal: `https://dev.abdm.gov.in`
- Sandbox swagger / Postman collections (NHA-hosted)
- HFR swagger: `https://facilitysbx.abdm.gov.in/swagger-ui.html`
- Beckn Protocol Health Specification (DSEP/UHI)
- NHA M1/M2/M3 milestone documentation
