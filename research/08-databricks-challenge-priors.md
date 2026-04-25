# 08 — Databricks Challenge Priors

Research date: 2026-04-25. Hackathon target: "Agentic Healthcare Maps" (Challenge 3) — multi-agent triage / bed prediction / inter-hospital routing on ~10k Indian hospital records.

## TL;DR — 3 most surprising / load-bearing facts

1. The literal phrase "Agentic Healthcare Maps" returns zero public hits; the parent program is almost certainly **Bharat Bricks Hacks 2026** (Databricks-sponsored India campus circuit, IIT Bombay edition Mar 28–29 2026), whose submission rules are explicit: a public repo with an **architecture diagram showing how Databricks components connect**, plus a 2-min demo and deployed prototype ([Devpost rules](https://bb2026-iitb.devpost.com/)).
2. Databricks' own April-2026 healthcare reference "AiChemy" hard-codes the exact pattern we should mirror — a **supervisor agent over domain skills** (literature, chem, evidence) connected via **MCP** and governed by **Agent Bricks** ([InfoWorld, 2026-04-06](https://www.infoworld.com/article/4154467/databricks-launches-aichemy-multi-agent-ai-for-drug-discovery.html)); on the patient side, the published `Patient Personalization Reference Architecture` literally says "**Mosaic AI–based agentic systems help pair the patient with the correct provider**" — i.e. our exact problem ([ref-arch](https://www.databricks.com/resources/architectures/healthcare-patient-personalization-reference-architecture)).
3. Past Databricks GenAI hackathon winners almost never bring novel data — they win on **Databricks-native plumbing** as theatre: medallion + Vector Search + MLflow eval + Databricks App UI (Exyte ReguBEAM, AITHENA, Care Cost Compass all follow this template) ([World Cup winners](https://www.databricks.com/blog/announcing-winners-generative-ai-world-cup), [Care Cost Compass](https://www.databricks.com/blog/care-cost-compass-agent-system-using-mosaic-ai-agent-framework)).

## Past Challenges & Sponsorships

| Date | Name | Scope | Sponsor track | Winners / notes |
|------|------|-------|---------------|-----------------|
| Apr–May 2024 | [Generative AI World Cup](https://www.databricks.com/blog/announcing-winners-generative-ai-world-cup) | Global, by industry (Healthcare & LS = 1 of 5) | Databricks (sole) | Grand: Exyte (ReguBEAM); APJ: AITHENA (legal RAG); Americas: Greenlight BioScience (image-pipe agent) |
| 2024 | [Databricks GenAI Hackathon (customers)](https://www.databricks.com/blog/announcing-winners-databricks-generative-ai-hackathon) | Customer-only | Databricks | 1st HEB "Shop It Easy"; 2nd Yahoo Smart Stock Screener; 3rd ITV "LIZZY"; HM: Karini Legal RAG, Sogeti multi-agent |
| Jun 9 2025 | [AI Agents Hackathon @ Data+AI Summit](https://databricks-hackathon.devpost.com/) | Invite-only SF, 6 hr | Two themes — **Community Wellness & Support Navigator** (literally healthcare-routing) + Accessible City Travel | Data partners: mimilabs (30 TB CMS/CDC/FDA), Bright Initiative (Google Maps), Nimble |
| Jun 2025 | 2025 Built-On Databricks Startup Challenge | B2B startups | Databricks Ventures | Grand: **RadiantGraph** — personalized healthcare-consumer engagement on Databricks ([2026 announcement](https://www.databricks.com/blog/announcing-2026-built-databricks-startup-challenge)) |
| Nov 5–14 2025 | [Free Edition Hackathon (inaugural)](https://www.databricks.com/blog/announcing-winners-inaugural-databricks-free-edition-hackathon) | Open, individual | Databricks | 1st VidMind; HM included a Biomedical Research Assistant Agent |
| Mar 28–29 2026 | [Bharat Bricks Hacks 2026 — IIT Bombay](https://bb2026-iitb.devpost.com/) | India campus circuit, ₹250k pool | Databricks (sole), 4 DBX judges | Concluded; full national finale via [bharatbricks.org](https://bharatbricks.org/) |
| May 22 2026 deadline | 2026 Built-On Databricks Startup Challenge | Startups, $1M+ | Databricks Ventures | Open — winners at Data+AI Summit, week of Jun 15 2026 |

No public page surfaces a literal "Agentic Healthcare Maps" brief. If our Challenge 3 sits inside the Bharat Bricks national finale, the public artefacts only show generic "Databricks Usage / Accuracy / Innovation / Presentation" judging — assume that rubric.

## Winning patterns

**Cross-cutting (every cohort):**
- Solo founders / 1–2 person teams routinely win — execution beats team size.
- Winners ship a **public GitHub + architecture diagram + ≤2-min demo + deployed link**. No diagram, no win.
- Domain framing > model novelty. Judges quote real $ savings or user counts in writeups.

**2024 cohort (GenAI World Cup + customer hackathon):**
- Data: tabular enterprise + retrieved docs (BIM regs, legal cases, member benefits, store inventory). Nobody won with novel ML — all retrieval + LLM.
- Architecture: medallion (bronze/silver/gold Delta) → Vector Search → Mosaic AI agent → Model Serving → app.
- UI: native **Databricks Apps** (Exyte, Greenlight) or chat-style. No team showed a custom-hosted React frontend without integrating it back via Apps.
- Wow moments: Exyte's "compliance verdict on a BIM model live"; Karini's "RAG over a real legal corpus, citations clickable."

**2025 cohort (AI Agents @ DAIS, Free Edition, customer agents):**
- Care Cost Compass (DBX-published reference) is the canonical pattern: **parallel async tool calls** (Vector Search × 2 + Online Tables) inside a custom PyFunc, deployed via Models-from-Code, evaluated with the Review App. Three demo "wow"s judges respond to: parallel-tool latency, Models-from-Code (no serialization pain), Review App for human feedback.
- BASF supervisor pattern: Genie agents (structured) + function-calling agents (unstructured) routed by a supervisor; Teams as the surface. The "voting/feedback in inference table" is the recurring theatrical beat.
- Free Edition winners (Nov 2025): judges scored on **Technical Complexity, Creativity, Presentation, Impact** — Presentation explicitly weighted. Winners over-invested in the storyline.

**2026 cohort (live):**
- AiChemy (Apr 6 2026): supervisor + skills + MCP for OpenTargets/PubMed/PubChem. Direct template for our setup — replace those skills with bed-availability, triage, transfer-coordination.
- Genie Code (Mar 11 2026): Databricks is itself shipping autonomous agents that "monitor Lakeflow pipelines and AI models to triage failures." Judges will recognise the pattern; mirror it in our ops story.

## Databricks reference architectures we should leverage

| Primitive | What it does | Why it matters for our build | Doc |
|---|---|---|---|
| **Mosaic AI Agent Framework + Agent Bricks (Supervisor Agent)** | Coordinate up to **20 sub-agents**: Genie Spaces, Knowledge Assistants, UC functions, MCP servers. Routing by description metadata, ACL-aware. | This *is* the architecture for triage→bed-predict→route→transfer. Each becomes a sub-agent the supervisor calls. | [Supervisor docs](https://docs.databricks.com/aws/en/generative-ai/agent-bricks/multi-agent-supervisor), [Supervisor blog (BASF)](https://www.databricks.com/blog/multi-agent-supervisor-architecture-orchestrating-enterprise-ai-scale), [Agent Bricks blog](https://www.databricks.com/blog/agent-bricks-governed-enterprise-agent-platform) |
| **Genie Spaces (Agent Mode)** | NL→SQL over curated Delta tables w/ UC metadata, descriptions, FK hints, SQL examples. | Our 10k-hospital table becomes a Genie space — judges will type "ICU beds in Pune <30 min" live. | [Mosaic AI 2025 announcements](https://www.databricks.com/blog/mosaic-ai-announcements-data-ai-summit-2025) |
| **Vector Search (storage-optimized, GA)** | Serverless vector DB on Delta, 7× cheaper, billions of vectors; UC-governed. | Index symptom→specialty mappings, hospital capability docs, transfer protocols. | [Mosaic AI 2025 announcements](https://www.databricks.com/blog/mosaic-ai-announcements-data-ai-summit-2025), [Mosaic Agent Framework](https://www.databricks.com/product/machine-learning/retrieval-augmented-generation) |
| **MLflow 3 (GenAI tracing + Model Registry + CLEARS eval)** | Trace agent steps, version prompts, register PyFunc/Models-from-Code, evaluate with correctness/latency/safety scorers. | Register our **Bed-Availability Predictor** in UC Model Registry; show traces on stage. CLEARS = the rubric Databricks itself uses. | [MLflow 3 GenAI](https://docs.databricks.com/aws/en/mlflow3/genai/), [Enhanced Agent Evaluation](https://www.databricks.com/blog/introducing-enhanced-agent-evaluation) |
| **Lakehouse Monitoring for GenAI** | Production drift / latency / quality dashboards over inference tables. | Show drift on the predictor between Delhi vs Mumbai data; closes the "production-ready" loop. | [Mosaic AI 2025 announcements](https://www.databricks.com/blog/mosaic-ai-announcements-data-ai-summit-2025) |
| **Unity Catalog + AI Gateway** | Governance, lineage, OAuth/MCP, PII guardrails, fallback routing across model providers. | Healthcare data → judges expect governance. AI Gateway is one slide that lands "production-grade." | [Agent Bricks blog](https://www.databricks.com/blog/agent-bricks-governed-enterprise-agent-platform) |
| **Lakeflow / Declarative Pipelines (DLT)** | Medallion ingest with built-in DQ rules, incremental, streaming-capable. | Bronze=raw 10k hospitals; silver=normalised; gold=routing-ready. Pre-built pattern in Patient Personalization ref-arch. | [Patient Personalization ref-arch](https://www.databricks.com/resources/architectures/healthcare-patient-personalization-reference-architecture) |
| **Online Tables** | Low-latency read replicas of Delta tables for serving. | Live bed counts have to come from Online Tables, not lakehouse scans. Care Cost Compass uses exactly this. | [Care Cost Compass blog](https://www.databricks.com/blog/care-cost-compass-agent-system-using-mosaic-ai-agent-framework) |
| **Databricks Apps (+ AppKit React SDK)** | Hosted React/Python frontends, identity-aware, deploy from repo. | The map UI lives here — not Vercel, not Streamlit external. Native = signal. | [Building Databricks Apps with React + Mosaic AI](https://www.databricks.com/blog/building-databricks-apps-react-and-mosaic-ai-agents-enterprise-chat-solutions), [appkit](https://github.com/databricks/appkit) |
| **Lakehouse for Healthcare accelerators** | HL7v2 ingest, FHIR interop, Disease Risk Prediction. | Use FHIR Interop accelerator names in our diagram even if we synthesise — speaks the judges' dialect. | [HLS solutions](https://www.databricks.com/solutions/industries/healthcare-and-life-sciences), [Lakehouse for HLS launch](https://www.databricks.com/blog/2022/03/09/introducing-lakehouse-for-healthcare-and-life-sciences.html) |
| **MCP connectors** | Managed OAuth MCP servers as agent tools. | If we wrap a 108-ambulance / ABDM stub as MCP, the supervisor calls it natively — visually matches AiChemy. | [AiChemy launch](https://www.infoworld.com/article/4154467/databricks-launches-aichemy-multi-agent-ai-for-drug-discovery.html) |

## 3 design signals likely to score with Databricks judges

**1. Wire the system as a Supervisor Agent over four named sub-agents — not as a monolithic LangChain script.**
Concretely: register `TriageAgent` (Knowledge Assistant over symptom→specialty corpus), `BedPredictor` (UC function calling an MLflow-served forecaster), `RouterAgent` (Genie Space over the hospital Delta table), `TransferCoordinator` (UC function wrapping an MCP tool that mocks 108/ABDM). The supervisor is `databricks.agents.SupervisorAgent` from [Agent Bricks](https://docs.databricks.com/aws/en/generative-ai/agent-bricks/multi-agent-supervisor). This visually mirrors AiChemy and BASF — judges (4 Databricks ICs) will recognise it in 10 seconds. Show the agent-list screenshot in the deck.

**2. Register the Bed-Availability Predictor in MLflow Model Registry under Unity Catalog, and show the Lakehouse Monitoring drift panel during the demo — even if drift is synthesised.**
The Care Cost Compass write-up and the Mosaic AI 2025 keynote both lean hard on MLflow tracing + monitoring as the "production maturity" beat. A 15-second moment where the presenter clicks into the Lakehouse Monitoring view, points at a quality-score dip, and says "agent #3 caught a regional drift overnight" hits the **Well-Architected** judging line that appears in *every* DBX rubric we found ([World Cup criteria](https://generativeai-worldcup.devpost.com/)). Avoid: a slide that just says "we used MLflow."

**3. Ship the demo as a Databricks App with a Genie Space embedded for live "type-and-query" theatre.**
Patterns we've seen reward this. (a) Native Apps deployment beats Vercel/Streamlit-external because hosting *inside* the lakehouse is the marketing pillar Databricks is pushing in 2026 ([Apps + Lakebase](https://www.databricks.com/blog/how-build-production-ready-data-and-ai-apps-databricks-apps-and-lakebase), [appkit SDK](https://github.com/databricks/appkit)). (b) A judge typing "Show me ICUs with ventilator capacity in Maharashtra" into a Genie box and watching SQL render is the single highest-leverage wow moment in Databricks demos right now — it's literally what Genie Code (Mar 2026) is selling. The map UI sits next to it; click a hospital and the supervisor agent narrates the routing decision with MLflow trace IDs visible.

Avoid: voice-only demos (108 audio stack is impressive but consumes too much demo time vs. the lakehouse-native signals judges actually score).

## Sources

- [Bharat Bricks Hacks 2026 — IIT Bombay (Devpost)](https://bb2026-iitb.devpost.com/)
- [Bharat Bricks Hacks 2026 (national)](https://bharatbricks.org/)
- [Databricks AI Agents Hackathon @ DAIS 2025 (Devpost)](https://databricks-hackathon.devpost.com/)
- [Generative AI World Cup hackathon (Devpost)](https://generativeai-worldcup.devpost.com/)
- [Announcing the Generative AI World Cup (blog)](https://www.databricks.com/blog/announcing-generative-ai-world-cup-2024-global-hackathon-databricks)
- [Generative AI World Cup winners (blog)](https://www.databricks.com/blog/announcing-winners-generative-ai-world-cup)
- [Databricks Generative AI Hackathon winners (blog)](https://www.databricks.com/blog/announcing-winners-databricks-generative-ai-hackathon)
- [Databricks Free Edition Hackathon launch (blog)](https://www.databricks.com/blog/databricks-free-edition-hackathon-show-world-whats-possible-data-and-ai)
- [Free Edition Hackathon winners (blog)](https://www.databricks.com/blog/announcing-winners-inaugural-databricks-free-edition-hackathon)
- [2026 Built-On Databricks Startup Challenge (blog)](https://www.databricks.com/blog/announcing-2026-built-databricks-startup-challenge)
- [Crushing your AI Hackathon on Databricks — 10 ideas (Medium)](https://medium.com/@AI-on-Databricks/crushing-your-ai-hackathon-on-databricks-10-ideas-c1bffc03c0b5)
- [Care Cost Compass agent reference (blog)](https://www.databricks.com/blog/care-cost-compass-agent-system-using-mosaic-ai-agent-framework)
- [Healthcare Patient Personalization Reference Architecture](https://www.databricks.com/resources/architectures/healthcare-patient-personalization-reference-architecture)
- [Lakehouse for Healthcare & Life Sciences launch (blog)](https://www.databricks.com/blog/2022/03/09/introducing-lakehouse-for-healthcare-and-life-sciences.html)
- [Databricks for HLS — solutions hub](https://www.databricks.com/solutions/industries/healthcare-and-life-sciences)
- [AiChemy multi-agent for drug discovery (InfoWorld, Apr 2026)](https://www.infoworld.com/article/4154467/databricks-launches-aichemy-multi-agent-ai-for-drug-discovery.html)
- [Mosaic AI Agent Framework product page](https://www.databricks.com/product/machine-learning/retrieval-augmented-generation)
- [Agent Bricks: governed enterprise agent platform (blog)](https://www.databricks.com/blog/agent-bricks-governed-enterprise-agent-platform)
- [Multi-Agent Supervisor architecture — BASF (blog)](https://www.databricks.com/blog/multi-agent-supervisor-architecture-orchestrating-enterprise-ai-scale)
- [Supervisor Agent docs (AWS)](https://docs.databricks.com/aws/en/generative-ai/agent-bricks/multi-agent-supervisor)
- [Mosaic AI announcements at DAIS 2025 (blog)](https://www.databricks.com/blog/mosaic-ai-announcements-data-ai-summit-2025)
- [MLflow 3 for GenAI docs](https://docs.databricks.com/aws/en/mlflow3/genai/)
- [Enhanced Agent Evaluation (blog)](https://www.databricks.com/blog/introducing-enhanced-agent-evaluation)
- [Building Databricks Apps with React + Mosaic AI (blog)](https://www.databricks.com/blog/building-databricks-apps-react-and-mosaic-ai-agents-enterprise-chat-solutions)
- [Production-ready Apps + Lakebase (blog)](https://www.databricks.com/blog/how-build-production-ready-data-and-ai-apps-databricks-apps-and-lakebase)
- [databricks/appkit (GitHub)](https://github.com/databricks/appkit)
- [Genie Code launch (PR)](https://www.databricks.com/company/newsroom/press-releases/databricks-launches-genie-code-bringing-agentic-engineering-data)
- [Author an AI agent and deploy it on Databricks Apps (docs)](https://docs.databricks.com/aws/en/generative-ai/agent-framework/author-agent)
