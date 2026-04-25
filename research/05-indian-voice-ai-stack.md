# 05 — Indian Voice AI Stack for Telephony (Hospital Reception Calls)

## TL;DR

1. **Global voice models degrade catastrophically over 8kHz PSTN.** ElevenLabs (tuned for 48kHz studio) loses its "human-like" advantage on phone calls. **Sarvam Bulbul v3 was trained on 8kHz telephony and outperformed ElevenLabs by 60% in blind listener preference** over degraded phone lines. For hospital reception desks where audio fidelity is non-negotiable, regional optimizers beat global brands.
2. **Bhojpuri is the Achilles heel.** 50M speakers, but **omitted from Sarvam, Krutrim, and most sovereign stacks**. ElevenLabs v3 supports it (not 8kHz-tuned). Bhashini supports it (subsidized govt). Edesy/OnDial support it natively. **Hard architectural constraint** — can't add custom Bhojpuri to ElevenLabs in 24h.
3. **Cost ceiling per 30s ICU inquiry call:** Edesy ₹2–3 end-to-end. Custom Twilio + Sarvam stack ~₹6.5 (₹0.12 STT + ₹0.60 TTS + ₹5.80 Twilio). ElevenLabs $0.10–0.17/min = 25–40× more expensive than regional optimizers.

> **★ INSIGHT (Killing Feature A — voice verifier)** — Our verifier fires only when prediction confidence <0.7 OR sample >2h old. At ~₹3/call we can spot-check ~300 hospitals per ₹1,000 of credit. Sarvam's free ₹1,000 sandbox + Twilio free tier is enough for an entire hackathon demo without spending real money.

---

## Language Quality at 8kHz Telephony

| Language | Grade | Notes |
|---|---|---|
| Hindi | A+ | All providers; native Hinglish code-switch (ICU/ventilator/oxygen mid-sentence) |
| Tamil | A | Agglutinative — long suffix-laden words. Tamglish code-switch fine |
| Telugu | A- | Agglutinative; verbose responses can blow latency budget |
| Marathi | A- | Distinct retroflex consonants. Strong urban demand → mature stacks |
| Bengali | B+ | Dialect drift between rural WB and urban Kolkata |
| **Bhojpuri** | **C+** | **Omitted by Sarvam/Krutrim. 50M speakers. Need Bhashini/Edesy/OnDial.** |

> **★ INSIGHT** — For Phase 1, Hindi is enough. Add Bhojpuri as a Phase 3 demo flex if we're calling rural Bihar — but pin a single Bihar-only path through Edesy or Bhashini, don't try to swap providers per-call mid-pipeline.

---

## Architecture: Pipeline vs End-to-End

### Sequential pipeline (standard)
```
PSTN → Twilio/SIP → STT → LLM → TTS → RTP → PSTN
```
Latency stack: STT ~300ms + LLM TTFT ~400ms + TTS TTFB ~200ms = **~900ms — at the conversational edge**. Above 1s and the receptionist hangs up.

**Production tricks:** WebSocket streaming, partial transcripts to LLM mid-utterance, TTS chunk streaming, intelligent endpointing.

### End-to-end S2S (Krutrim Dhwani, OpenAI Realtime)
Audio → multimodal LLM → audio. Eliminates ASR error cascade, preserves prosody. **Higher cost, less control over intermediate logic** (e.g. can't intercept "ICU" keyword to do a DB lookup mid-conversation).

> **★ INSIGHT** — Pipeline beats S2S for our use case because we *want* to intercept the response text — "yes, 3 ICU beds free" must trigger a write to the predictor's ground-truth feedback store. S2S audio-to-audio buries that signal.

---

## Provider Matrix

### Bhashini (Govt of India / MeitY)
- 22 languages, **incl. Bhojpuri**
- ~1s latency per sentence (sluggish for ICU inquiry)
- **₹250/month for 50k chars/day** — effectively free at our volume
- Sovereign data layer, but private platforms tune latency more aggressively

### Sarvam AI — **the recommended core**
- Saaras v3 STT: 22 langs, native code-switch. **Bhojpuri absent.**
- Bulbul v3 TTS: 11 langs. **Trained on 8kHz** → **60% blind preference over ElevenLabs on PSTN**.
- Round-trip ~800ms (Saaras + std LLM + Bulbul)
- Pricing: STT ₹30/hour, TTS ₹30/10k chars
- Sandbox: **₹1,000 free credits**

### Krutrim (Ola group)
- Dhwani end-to-end S2S, 9 langs (Bengali, Gujarati, Hindi, Kannada, Malayalam, Marathi, Tamil, Telugu + Eng). **No Bhojpuri.**
- BLEU 57.7 (Eng→Hindi), 43.3 (Eng→Marathi)
- Own H100 cloud — tight latency only if app hosted in Krutrim VPC
- TTS ₹4.42/min, STT ₹24/hour. Free dev tier.

### ElevenLabs
- v3: 74 langs incl. Bhojpuri (not 8kHz-tuned for it)
- Flash v2.5: ~75ms TTFB
- Telephony partners: Ozonetel, Exotel, Plivo
- **8kHz weakness** → loses advantage on PSTN
- ~$0.10–0.17/min — **expensive for transactional calls**
- Free tier: 10k chars/month

### Deepgram
- Nova-3 STT: fastest, best noise handling
- Flux: native turn-detection (kills VAD complexity)
- STT supports Hindi + Tamil only of our targets
- **Aura TTS: no Indian language support** → must bifurcate (Deepgram STT + Sarvam/ElevenLabs TTS)
- $0.0092/min STT, $200 free credit

### Twilio ConversationRelay (orchestration only)
- Median <0.5s, P95 0.725s
- Handles SIP/RTP/echo cancellation natively
- $0.07/min on top of telephony termination

### Edesy — **the dedicated regional alternative**
- End-to-end (STT+LLM+TTS+telephony)
- **Native Bhojpuri**
- Sub-500ms latency
- ~$0.04/min (₹4–6/min)

### OnDial
- Explicit Bihar/Bhojpuri positioning
- ChatGPT + native Bhojpuri TTS
- Outbound-call-focused

---

## Costs at 30-Second ICU Inquiry

| Stack | Per-call cost | Notes |
|---|---|---|
| **Edesy** | ~₹2–3 | Flat all-in |
| **Sarvam custom + Twilio** | ~₹6.5 | ₹0.12 STT + ₹0.60 TTS + ₹5.80 Twilio orchestration |
| **Bhashini** | ~₹0 (subsidized tier) | But ~1s latency penalty |
| **ElevenLabs + Twilio** | ₹13–22 | 25–40× regional optimizers, weak on 8kHz |

> **★ INSIGHT** — Twilio's $0.07/min is the dominant cost in any custom pipeline. If we use Edesy, that goes away — but we lose the demo-able STT/LLM/TTS architecture diagram. **For Databricks judges who want to see pipeline plumbing, Sarvam+Twilio reads better; for cost discipline at scale, Edesy wins.**

---

## Recommended Stack for "Do You Have an ICU Bed?"

### Operational constraints
- Chaotic ambient acoustic environment (hospital reception)
- Localized dialect, code-switch with English medical terms
- Zero tolerance for >1s latency
- 8kHz cellular degradation

### The build (custom pipeline)
1. **Twilio ConversationRelay** — SIP/RTP/echo, <500ms edge
2. **Sarvam Saaras v3 (STT)** — code-switch + 22 Indian langs (swap to Bhashini/Edesy if Bihar/Bhojpuri)
3. **LLM** — Sarvam-30B or fast LLaMA-3 inference, single intent: yes/no/N beds + graceful close
4. **Sarvam Bulbul v3 (TTS)** — **the differentiator**. 8kHz-native, sounds professional over PSTN

Total round-trip: ~800ms. Cost: ~₹6.5/call.

### The pragmatic alternative
**Edesy end-to-end** — single API, sub-500ms, ~₹3/call, native Bhojpuri. Use when team has no DevOps capacity for multi-vendor orchestration.

### What to reject
- ElevenLabs: priced for studio quality we can't transmit anyway
- Deepgram alone: no Indian-language TTS
- Krutrim: no Bhojpuri, latency commitments only inside their VPC
- OpenAI Realtime API: no granular intermediate-text intercept

---

## Sources
- Sarvam AI Saaras v3 / Bulbul v3 product docs
- Bhashini API pricing (MeitY)
- Krutrim AI Studio pricing
- ElevenLabs v3 + Flash v2.5 docs
- Deepgram Nova-3 / Aura-2 / Flux release notes
- Twilio ConversationRelay product page
- Edesy / OnDial product pages
- Independent 8kHz blind-listener preference test (Sarvam vs ElevenLabs)
