# 09 — Databricks Editions: Free Edition vs Trial for Work

> Compiled 2026-04-25 from official Databricks docs + community posts via Tavily research and direct WebFetch verification. Cross-checks claims surfaced during spec review (`docs/superpowers/specs/2026-04-25-healthcare-multiagent-design.md`).

## TL;DR

1. **Free Edition is too restrictive for the spec we want to ship.** It explicitly blocks Mosaic AI Supervisor Agent + Knowledge Assistant + Foundation Model Fine-tuning + Online Tables + Lakebase, caps Vector Search to 1 endpoint with no Direct Vector Access, allows only 1 Databricks App that auto-stops after 24h, and forbids commercial use.
2. **Trial for Work (14-day Premium) restores ~95% of the architecture** — Supervisor Agent works (with preview enablement), multiple Apps, scaleable SQL warehouses, commercial-use POC permitted, $400 credits, classic compute access.
3. **Two caveats survive the upgrade:** (a) outbound internet is *still* restricted to a limited set of trusted domains in the trial, and (b) Foundation Model Fine-tuning is region-locked to AWS `us-east-1` / `us-west-2` and stuck in Public Preview — Trial inclusion not explicitly documented. **Both must be validated in-product H 0 before they're in the build plan.**

> **★ INSIGHT (decision)** — We default to Trial for Work, not Free Edition. Brief says "optimized for Free Edition" but does not *require* it; Trial gives the Premium-tier feature surface that AiChemy / Care Cost Compass / BASF reference architectures rely on. The cost is a 14-day expiry — every artifact (notebooks, models, App URL screenshots, demo video) must be backed up to GitHub before day 14.

---

## Free Edition — feature audit

| # | Feature | Status | Citation |
|---|---|---|---|
| 1 | Serverless compute (general) | ✅ AVAILABLE (limited size + usage) | [free-edition-limitations][lim] |
| 2 | Serverless GPU compute (A10/H100) | ❌ NOT AVAILABLE — *"GPUs are not supported"* | [lim][] |
| 3 | Unity Catalog | ✅ AVAILABLE (1 metastore) | [lim][] |
| 4 | Lakeflow / DLT | ✅ AVAILABLE — capped at 1 active pipeline per type | [lim][] |
| 5 | Jobs orchestration | ✅ AVAILABLE — capped at 5 concurrent job tasks | [lim][] |
| 6 | MLflow (Experiments + Tracing + Registry under UC) | ✅ AVAILABLE | [mlflow][] |
| 7 | Lakehouse Monitoring | ⚠ UNCLEAR — not enumerated either way | [lim][] |
| 8 | Mosaic AI Vector Search | ⚠ LIMITED — *"One Vector Search endpoint, limited to one Vector Search unit. Direct Vector Access is not supported."* | [lim][] |
| 9 | Mosaic AI Model Serving (custom endpoints) | ⚠ LIMITED — CPU only, *"No GPU serving endpoints… No provisioned throughput… No custom models on GPU or batch inference"* | [lim][] |
| 10 | Foundation Model APIs (pay-per-token) | ✅ AVAILABLE — *"experimenting with foundation models"* | [free-edition][fe] |
| 11 | Foundation Model Fine-tuning (Mosaic AI Model Training) | ❌ NOT AVAILABLE — requires Serverless GPU which FE excludes | [lim][] + [fmt][] |
| 12 | Mosaic AI Agent Bricks — Supervisor Agent | ❌ NOT AVAILABLE — *"Knowledge Assistant and Supervisor Agent"* in unsupported list | [lim][] |
| 13 | Mosaic AI Agent Bricks — Knowledge Assistant | ❌ NOT AVAILABLE — same line | [lim][] |
| 14 | Mosaic AI Agent Framework (lower-level — LangGraph/PyFunc) | ✅ AVAILABLE | [mlflow][] |
| 15 | Genie Spaces (NL→SQL) | ✅ AVAILABLE — *"interact with and visualize your data using natural-language prompts"* | [fe][] |
| 16 | Genie Code (autonomous multi-step agent) | ✅ AVAILABLE — *"Genie Code can suggest, explain, and fix code directly within notebooks, queries, and files"* | [fe][] |
| 17 | Databricks Apps | ⚠ LIMITED — *"one Databricks App per account, runs for up to 24 hours after start, update, or redeploy before being automatically stopped"* | [lim][] |
| 18 | Lakebase (Postgres OLTP) | ❌ NOT AVAILABLE — *"Lakebase database instances"* in unsupported list | [lim][] |
| 19 | Online Tables | ❌ NOT AVAILABLE — *"Online tables"* in unsupported list | [lim][] |
| 20 | R / Scala languages | ❌ NOT AVAILABLE — *"R and Scala"* in unsupported list | [lim][] |
| 21 | Custom workspace storage locations (own S3/GCS) | ❌ NOT AVAILABLE | [lim][] |
| 22 | Outbound internet access | ⚠ RESTRICTED — *"outbound internet access is restricted to a limited set of trusted domains"* | [lim][] |
| 23 | Commercial use | ❌ NOT ALLOWED — *"Free Edition accounts are meant for non-commercial use"* | [lim][] |
| 24 | Account expiry | Forever free; deleted after prolonged inactivity | [lim][] |

### Free Edition hard limits

| Resource | Limit |
|---|---|
| Workspaces / metastores | 1 / 1 per account |
| SQL warehouse | 1, fixed at `2X-Small` |
| Lakeflow pipelines | 1 active per pipeline type |
| Concurrent job tasks | 5 per account |
| Vector Search | 1 endpoint, 1 VS unit, Delta-sync only |
| Apps | 1 per account, **auto-stops after 24h** |
| Auth | email OTP / Google / Microsoft only — no SSO/SCIM |
| Quota over-run penalty | compute shut down for the rest of the day (or month in extreme cases) |

---

## Trial for Work — feature audit

> 14-day Premium trial. Up to $400 credits. Designed for commercial use / business evaluation. Production account with multi-workspace and classic compute. After expiry: must add payment method or assets are deleted 60 days later.

| # | Feature | Status | Notes |
|---|---|---|---|
| 1 | Serverless GPU compute (A10/H100) | ⚠ CONFLICTING DOCS — H100 starter notebooks exist on docs site, but trial-specific doc says *"no GPU access; only CPU resources"*. **Test in product.** | [sgc][] vs [trial][] |
| 2 | Mosaic AI Foundation Model Fine-tuning | ⚠ LIMITED — Public Preview, region-locked to `us-east-1` / `us-west-2`. Trial inclusion not explicitly stated. | [fmt][] |
| 3 | Mosaic AI Agent Bricks — Supervisor Agent | ✅ AVAILABLE (with prerequisites) — needs Serverless compute + UC + Mosaic AI Model Serving + non-zero serverless budget policy enabled | [supervisor-doc][] |
| 4 | Mosaic AI Agent Bricks — Knowledge Assistant | ✅ AVAILABLE (with prerequisites) — same enablement requirements + Production monitoring for MLflow (Beta) | [ka-doc][] |
| 5 | Mosaic AI Vector Search | ⚠ LIMITED — storage-optimized in Public Preview; *"limits vector search to one endpoint with a scale capped to one vector search unit"* (same as Free Edition) | [vs-doc][] + [trial][] |
| 6 | Foundation Model APIs (pay-per-token) | ✅ AVAILABLE — full platform access for two weeks | [fmapi][] + [try][] |
| 7 | Foundation Model APIs — provisioned throughput | ❌ NOT AVAILABLE — *"Provisioned throughput endpoints are not supported in the trial workspace; a paid plan is required"* | [community][] |
| 8 | Online Tables | ✅ likely AVAILABLE (Premium feature; not specified for trial but trial = "full platform access") | [try][] |
| 9 | Lakebase | ✅ likely AVAILABLE (same logic) | [oltp][] |
| 10 | Lakehouse Monitoring | ✅ likely AVAILABLE (Premium feature; trial gives full platform) | [lhm][] |
| 11 | MLflow 3 (Tracing + Registry + Experiments) | ✅ AVAILABLE | [mlflow][] |
| 12 | Genie Spaces (NL→SQL) | ✅ AVAILABLE — needs Databricks SQL entitlement which trial provides | [genie][] |
| 13 | Genie Code (autonomous multi-step agent) | ✅ AVAILABLE | [genie-code][] |
| 14 | Databricks Apps (multiple, no 24h auto-stop) | ✅ AVAILABLE — *"limited number of apps per workspace"* but no auto-stop | [apps][] |
| 15 | Multiple workspaces / metastores per account | ✅ AVAILABLE — *"production account with access to account console, ability to add multiple workspaces"* | [try][] |
| 16 | Outbound internet access | ⚠ RESTRICTED — *"the free trial has limited external network access; blocked public datasets must be manually downloaded"* | [trial][] |
| 17 | SQL warehouses (size and count) | ⚠ LIMITED — *"limits SQL warehouses to one per workspace, scaling to a maximum of 50 DBUs per hour"* (much better than FE's fixed 2X-Small) | [trial][] |
| 18 | Concurrent job tasks | ⚠ NOT EXPLICITLY DOCUMENTED for trial; assume Premium-tier defaults | [trial][] |
| 19 | Multiple Lakeflow pipelines | ⚠ NOT EXPLICITLY DOCUMENTED; assume Premium-tier defaults | [trial][] |
| 20 | Custom workspace storage locations (own S3/GCS) | ✅ likely AVAILABLE — Premium feature | [storage][] |
| 21 | Commercial use | ✅ ALLOWED — *"Designed for commercial use… work with any data on any cloud"* | [try][] |
| 22 | Trial duration | 14 days from sign-up | [express][] |
| 23 | Cost after trial | Must add payment method to continue. Otherwise: assets deleted 60 days after trial ends. Data may be deleted immediately. | [express][] |
| 24 | Credit budget | Up to $400 in credits | [try][] |

---

## What Trial for Work changes vs Free Edition

### ✅ Unblocked (was FE-blocked)

- **Mosaic AI Supervisor Agent + Knowledge Assistant** — back ON. AiChemy 1:1 mirror architecture viable.
- **Online Tables + Lakebase** — back ON. Live serving of Trust scores possible.
- **Multiple Databricks Apps** (no 24h auto-stop) — Patient flow + Doctor copilot + NGO dashboard as 3 separate apps.
- **Multiple workspaces** — production account.
- **Commercial use** — POC pitch valid.
- **SQL warehouse scaling** (up to 50 DBU/h vs fixed 2X-Small) — Genie Code fast.
- **Custom storage locations** — own S3/GCS bucket viable.

### ⚠ Still constrained

- **Outbound internet access remains restricted** — Voice MCP to external Twilio/Sarvam/Fish Audio at risk; need whitelist test in product.
- **Vector Search caps** — still 1 endpoint, 1 VS unit, both editions. Storage-optimized still Public Preview.
- **Foundation Model Fine-tuning** — region-locked, Public Preview, trial inclusion unverified.
- **Provisioned throughput** — not in trial.

### 💀 New Trial-specific constraints

- **14-day expiry** — assets deleted 60 days post-expiry if no payment method added.
- **$400 credit budget** — careful with GPU spend if available; LoRA on A10 ≈ $1-3, multi-hour H100 = serious.
- **Trial ≠ production deployment** — long-term commercial use requires upgrade.

---

## Validation gates — run in-product H 0 before committing build plan

These tests block downstream work; run them first.

### Test 1: Outbound network whitelist
```python
import requests
for url in [
    "https://api.openai.com/v1/models",
    "https://api.anthropic.com/v1/models",
    "https://api.twilio.com",
    "https://api.fish.audio",
    "https://api.sarvam.ai",
    "https://huggingface.co/api/models",
]:
    try:
        r = requests.get(url, timeout=5)
        print(f"{url}: {r.status_code}")
    except Exception as e:
        print(f"{url}: BLOCKED ({type(e).__name__})")
```
Outcome decides whether Voice MCP uses external providers or falls back to Foundation Model APIs (intra-Databricks) only.

### Test 2: GPU compute availability
- Compute → Create cluster → check node-type dropdown for GPU options (`g4dn.*`, `g5.*`, `p4`, `p5`)
- Or in notebook: try `mlflow_deployments.list_endpoints()` and check for any GPU-labeled training endpoint
- Verdict gates whether Foundation Model Fine-tuning is in plan.

### Test 3: Foundation Model APIs catalog
```python
import mlflow.deployments
client = mlflow.deployments.get_deploy_client("databricks")
endpoints = [e['name'] for e in client.list_endpoints()]
print(endpoints)
```
Should include `databricks-claude-opus-4-7`, `databricks-meta-llama-3-3-70b-instruct`, etc. Confirms which models we can call.

### Test 4: Workspace region
- Settings → Workspace → check region.
- Must be `us-east-1` or `us-west-2` for Foundation Model Fine-tuning Public Preview access.

### Test 5: Supervisor Agent enablement
- Left nav → look for Mosaic AI / Agents / Agent Bricks
- May need to enable Public Preview features under Account → Previews
- Confirm before designing supervisor flow

### Test 6: Vector Search storage-optimized index
- Compute → Vector Search → Create endpoint → check option `Storage-optimized`
- Storage-optimized was March 2026 GA in some configs, still Preview elsewhere

### Test 7: Lakehouse Monitoring
- Open any UC table → Quality / Monitoring tab
- "Create monitor" button enabled = ✅
- If absent → fall back to hand-rolled MLflow drift notebook scheduled as a job

### Test 8: Multi-App deployment
- Compute → Apps → check "Create app" works AND no 24h auto-stop banner appears
- Try deploying a second app to confirm multi-app

### Test 9: Apps assets persist beyond demo
- Deploy small placeholder App now
- Verify `*.databricksapps.com` URL resolves
- Backup URL + screenshot before any expiry concerns

---

## Decisions for spec

Default to **Trial for Work** for the build, with these conditional branches:

1. **If outbound network includes Twilio/Sarvam** → Voice MCP runs as designed (Tier 2 fallback live)
2. **If outbound network blocks them** → Voice MCP becomes intra-Databricks only (use Foundation Model APIs Whisper-equivalent for STT, Bulbul-equivalent for TTS if hosted; otherwise mock-only for demo)
3. **If GPU compute is in trial** → assign one team member (Mubarak / Danish pair) to LoRA fine-tune Llama-3.2-3B on Hindi medical extraction (time cap 6h)
4. **If GPU compute is NOT in trial** → friend's fine-tune work moves to external Colab T4 (independent track), trial only for serving the resulting checkpoint via CPU Model Serving
5. **If Foundation Model Fine-tuning region-blocked** (workspace not in us-east-1/us-west-2) → drop Mosaic AI Model Training entirely; Colab + CPU serving is the path

---

## Backup plan — when trial expires

- Mirror everything to GitHub before day 14:
  - Notebooks (export `.dbc` archive)
  - MLflow runs (download via API)
  - Datasets (data/raw/ already gitignored — manual S3 backup)
  - App source code (lives in repo anyway)
- Demo video must be recorded before day 14 — assets may break after.
- If we win and need to re-demo, upgrade the trial (add payment) or republish to a clean Premium account.

---

## Sources

[fe]: https://docs.databricks.com/aws/en/getting-started/free-edition
[lim]: https://docs.databricks.com/aws/en/getting-started/free-edition-limitations
[trial]: https://docs.databricks.com/aws/en/getting-started/free-trial
[try]: https://www.databricks.com/try-databricks
[express]: https://docs.databricks.com/aws/en/getting-started/express-setup
[fmt]: https://docs.databricks.com/aws/en/large-language-models/foundation-model-training/
[fmapi]: https://docs.databricks.com/aws/en/machine-learning/foundation-model-apis/
[supervisor-doc]: https://docs.databricks.com/aws/en/generative-ai/agent-bricks/multi-agent-supervisor
[ka-doc]: https://docs.databricks.com/aws/en/generative-ai/agent-bricks/knowledge-assistant
[mlflow]: https://docs.databricks.com/aws/en/mlflow/
[vs-doc]: https://docs.databricks.com/aws/en/vector-search/vector-search
[apps]: https://docs.databricks.com/aws/en/dev-tools/databricks-apps/
[genie]: https://docs.databricks.com/aws/en/genie/
[genie-code]: https://docs.databricks.com/aws/en/genie/code/
[lhm]: https://docs.databricks.com/sap/en/lakehouse-monitoring
[oltp]: https://docs.databricks.com/aws/en/oltp/
[storage]: https://docs.databricks.com/aws/en/files/write-data
[sgc]: https://docs.databricks.com/aws/en/machine-learning/ai-runtime/examples/tutorials/sgc-api-h100-starter
[community]: https://community.databricks.com/t5/databricks-free-edition-help/databricks-free-trial-model-serving-error/td-p/130899
[winners]: https://www.databricks.com/blog/announcing-winners-inaugural-databricks-free-edition-hackathon

- Free Edition (FE) main page: <https://docs.databricks.com/aws/en/getting-started/free-edition>
- Free Edition limitations: <https://docs.databricks.com/aws/en/getting-started/free-edition-limitations>
- Trial main page: <https://www.databricks.com/try-databricks>
- Trial doc: <https://docs.databricks.com/aws/en/getting-started/free-trial>
- Trial vs Free Edition comparison: <https://docs.databricks.com/aws/en/getting-started/free-trial-vs-free-edition>
- Express setup (trial signup): <https://docs.databricks.com/aws/en/getting-started/express-setup>
- Foundation Model Training docs: <https://docs.databricks.com/aws/en/large-language-models/foundation-model-training/>
- Foundation Model APIs: <https://docs.databricks.com/aws/en/machine-learning/foundation-model-apis/>
- Mosaic AI Supervisor Agent docs: <https://docs.databricks.com/aws/en/generative-ai/agent-bricks/multi-agent-supervisor>
- Mosaic AI Knowledge Assistant docs: <https://docs.databricks.com/aws/en/generative-ai/agent-bricks/knowledge-assistant>
- Mosaic AI Vector Search docs: <https://docs.databricks.com/aws/en/vector-search/vector-search>
- Databricks Apps docs: <https://docs.databricks.com/aws/en/dev-tools/databricks-apps/>
- Genie Spaces docs: <https://docs.databricks.com/aws/en/genie/>
- Genie Code docs: <https://docs.databricks.com/aws/en/genie/code/>
- AI Runtime / Serverless GPU compute: <https://docs.databricks.com/aws/en/machine-learning/ai-runtime/examples/tutorials/sgc-api-h100-starter>
- Free Edition Hackathon winners blog: <https://www.databricks.com/blog/announcing-winners-inaugural-databricks-free-edition-hackathon>
- Community post on trial provisioned throughput limit: <https://community.databricks.com/t5/databricks-free-edition-help/databricks-free-trial-model-serving-error/td-p/130899>
- Unsloth (LoRA fine-tune library): <https://github.com/unslothai/unsloth>
- Apple MLX (M-series fine-tune): <https://github.com/ml-explore/mlx>
- MLX-LM (Llama on Apple Silicon): <https://github.com/ml-explore/mlx-lm>
