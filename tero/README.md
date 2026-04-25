# Tero — твой README

> Главная спека: `../docs/superpowers/specs/2026-04-25-healthcare-multiagent-design.md`
> Контракты JSON: `../contracts/`
> Дедлайн: **19 часов** от старта работы (2026-04-25)
> Команда: Mubarak (Triage), Mian (Predictor+DLT), Arushi (App)

## Что ты делаешь (revised после agent review)

3 подпапки. **TransferCoordinator передан Mubarak'у** — у тебя был 150% load, агенты review это поймали.

| Подпапка | Компонент | Стек | Phase |
|---|---|---|---|
| `voice/` | Voice MCP — FastAPI hosted as Databricks App. Hybrid stack: **Fish Audio (TTS, твой готовый engine) + OpenAI gpt-4o-audio (STT) + GPT-4o function calling (LLM)**. Не использует MCP protocol — UC function вызывает HTTP endpoint напрямую. | FastAPI, Fish Audio WS, OpenAI Realtime, Databricks Apps | 1-2 |
| `supervisor/` | Mosaic AI Supervisor Agent — оркестратор над 4 sub-agents | Python, Agent Bricks, MLflow | 1-2 |
| `router-config/` | Genie Space configuration над hospitals Delta table | YAML/SQL, Genie Spaces | 1 |

`transfer/` папка остаётся в `tero/` пустой как .gitkeep — реальная работа теперь в `mubarak/transfer/`.

## Порядок работы (19 часов жёстко)

### H 0-1 — провизионинг + spike (1ч)
- [ ] Databricks workspace + Unity Catalog perms для всех 4
- [ ] Spike: hello-world Mosaic AI Agent Bricks Supervisor
- [ ] Spike: Databricks App с appkit (для Arushi на старте)

### H 1-5 — Voice MCP (4ч, твой Fish Audio + OpenAI hybrid)
- [ ] `voice/`: FastAPI + WS endpoint skeleton (deploy таргет = Databricks App, не standalone)
- [ ] Импортить Fish Audio WS engine из `~/Desktop/Projects/Active/ai_hack/fishaudio/src/` — это **TTS слой**
- [ ] Pre-generate Hindi prompts в Fish Audio при старте → cache audio: «Kya aapke paas {specialty} ke liye bed khali hai?»
- [ ] OpenAI gpt-4o-audio для **STT** (заменяет Deepgram per agent review)
- [ ] OpenAI GPT-4o function calling для **LLM/parse** → структурный output без отдельного парсера
- [ ] Endpoint `/voice/verify_bed`: вход = `VoiceVerifyInput` → выход = `VoiceOutput` (см. `contracts/schemas.py`)
- [ ] 3 режима через env `VOICE_MODE`: `mock` (default), `realtime` (live OpenAI), `twilio` (Phase 3)
- [ ] Контракт-тест: output validates против `VoiceOutput` Pydantic модели
- [ ] **`voice_output.json` уже в `contracts/`** — Mubarak'a и Arushi уже разблокированы

### H 5-11 — Supervisor (6ч)
- [ ] `supervisor/` Python package
- [ ] Зарегистрировать 4 sub-agents через description metadata (Triage / BedPredictor / Router / TransferCoord / Voice)
- [ ] Routing logic: intent classifier (patient / doctor) → sub-agent sequence
- [ ] Confidence-trigger: `min(BedPredictor.confidence) < 0.7 OR sample_age > 2h` → invoke Voice
- [ ] MLflow tracing on
- [ ] Aggregator: соединяет JSON outputs в `SupervisorResponse` (см. `contracts/schemas.py`)
- [ ] Mock layer: читает все 4 mock JSON из `contracts/*_output.json`
- [ ] Smoke test: end-to-end с mock'ами проходит

### H 11-13 — Genie Space + Router config (2ч)
- [ ] Genie Space над silver hospitals Delta table
- [ ] 5 example queries: «ICU beds in Pune <30 min», «cardiology hospitals in Maharashtra», etc
- [ ] Sample SQL для FK hints

### H 13-16 — Integration prep + demo theatre (3ч)
- [ ] Pre-record fallback audio для каждого demo момента (страховка из спеки Section 11b)
- [ ] Demo screenshot capture: MLflow lineage, Lakehouse Monitoring, Genie SQL
- [ ] Demo script timing rehearsal (см. Section 11a главной спеки — 2 минуты по секундам)

### H 16-18 — Integration day (2ч)
- [ ] Заменить mock-вызовы в Supervisor на реальные UC fn / Knowledge Assistant invocations
- [ ] End-to-end test: Patient flow + Doctor flow (Mubarak пишет E2E)
- [ ] Demo theatre проверка: на каждой секунде что-то Databricks-нативное движется

### H 18-19 — Demo rehearsal + slides (1ч)
- [ ] 3 полных прогона демо
- [ ] 1 прогон с `VOICE_MODE=mock` (fallback drill — проверить что демо не ломается без OpenAI)
- [ ] Слайды (Arushi помогает): архитектурная диаграмма + human story

## Что эмитчишь

- `SupervisorResponse` — финальный ответ для Databricks App (см. `contracts/schemas.py`)
- `VoiceOutput` — voice verifier результат
- `RouterOutput` — ranked list (Genie запрос завернут)

(TransferOutput теперь у Mubarak'a)

## Что потребляешь (mocks из `contracts/`)

- `contracts/triage_output.json` (Mubarak)
- `contracts/predictor_output.json` (Mian)
- `contracts/transfer_output.json` (Mubarak)

Когда реальные готовы — Supervisor вызывает их вместо чтения mock JSON.

## Demo theatre за тобой

В каждый момент демо что-то Databricks-нативное должно двигаться на экране. Список проверок — Section 9 главной спеки.
