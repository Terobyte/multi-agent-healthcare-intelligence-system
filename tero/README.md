# Tero — твой README

> Главная спека: `../docs/superpowers/specs/2026-04-25-healthcare-multiagent-design.md`
> Контракты JSON: `../contracts/`
> Дедлайн: **19 часов** от старта работы (2026-04-25)
> Команда: Mubarak (Triage), Mian (Predictor+DLT), Arushi (App)

## Что ты делаешь

4 подпапки, каждая — отдельный мини-проект.

| Подпапка | Компонент | Стек | Phase |
|---|---|---|---|
| `voice/` | Voice MCP server — Fish Audio + STT/TTS, Hindi prompts | FastAPI, Fish Audio WS, Deepgram, MCP | 1-2 |
| `supervisor/` | Mosaic AI Supervisor Agent — оркестратор над 4 sub-agents | Python, Agent Bricks, MLflow | 1-2 |
| `transfer/` | TransferCoordinator — UC fn + 108/ABDM mock + FHIR snippet | Python, UC functions, MCP | 2 |
| `router-config/` | Genie Space configuration над hospitals Delta table | YAML/SQL, Genie Spaces | 1 |

## Порядок работы (19 часов жёстко)

### H 0-1 — провизионинг + spike (1ч)
- [ ] Databricks workspace + Unity Catalog perms для всех 4
- [ ] Spike: hello-world Mosaic AI Agent Bricks Supervisor
- [ ] Spike: Databricks App с appkit (для Arushi на старте)

### H 1-5 — Voice MCP (4ч, готовые движки)
- [ ] Создать `voice/`: FastAPI + MCP server skeleton
- [ ] Импортить Fish Audio WS engine из `~/Desktop/Projects/Active/ai_hack/fishaudio/src/`
- [ ] Импортить microphone engine
- [ ] Endpoint `/mcp/verify_bed`: вход `{hospital_id, question_template}` → выход по `VoiceMCP.output`
- [ ] Hindi prompt: «Kya aapke paas {specialty} ke liye bed khali hai?»
- [ ] STT через Deepgram для парсинга ответа
- [ ] Mock-режим (`MOCK=true` env var) — без реального звонка для демо-страховки
- [ ] Smoke test: `pytest tests/smoke.py`
- [ ] Положить `mock_output.json` в папку для остальных

### H 5-11 — Supervisor (6ч)
- [ ] `supervisor/` Python package
- [ ] Зарегистрировать 4 sub-agents через description metadata (Triage / BedPredictor / RouterAgent / TransferCoord / Voice MCP)
- [ ] Routing logic: intent classifier (patient / doctor) → sub-agent sequence
- [ ] Confidence-trigger: `min(BedPredictor.confidence) < 0.7 OR sample_age > 2h` → invoke Voice MCP
- [ ] MLflow tracing on
- [ ] Aggregator: соединяет JSON outputs в финальный response
- [ ] Mock layer: все 4 sub-agents возвращают mock JSON (читаются из `../*/mock_output.json`)
- [ ] Smoke test: end-to-end с mock'ами проходит

### H 11-13 — Genie Space + Router config (2ч)
- [ ] Genie Space над silver hospitals Delta table
- [ ] 5 example queries в Genie: «ICU beds in Pune <30 min», «cardiology hospitals in Maharashtra», и т.д.
- [ ] Sample SQL для FK hints

### H 13-16 — TransferCoordinator (3ч)
- [ ] UC function: `{sending_hospital_id, patient_summary, receiving_hospitals}` → выход `TransferCoordinator.output`
- [ ] Mock 108: фейковый ETA countdown
- [ ] Mock ABDM: FHIR JSON snippet + PDF URL
- [ ] D2D handoff form generator

### H 16-18 — Integration day (2ч)
- [ ] Заменить mock-вызовы в Supervisor на реальные UC fn / Knowledge Assistant invocations
- [ ] End-to-end test: Patient flow + Doctor flow
- [ ] Demo theatre проверка: на каждой секунде что-то Databricks-нативное движется

### H 18-19 — Demo rehearsal + slides (1ч)
- [ ] Прогон демо 3 раза
- [ ] Слайды (Arushi помогает): архитектурная диаграмма + human story + лайв демо

## Что эмитчишь

- `SupervisorResponse` — финальный ответ для Databricks App
- `VoiceMCP.output` — verifier результат
- `TransferCoordinator.output` — receivers + packet + ambulance ETA
- `RouterAgent.output` — ranked list (Genie запрос завернут)

## Что потребляешь (mocks)

- `mubarak/triage/mock_output.json`
- `mian/predictor/mock_output.json`

Когда они готовы — заменяешь mock'и на реальные вызовы.

## Demo theatre за тобой

В каждый момент демо что-то Databricks-нативное должно двигаться на экране. Список проверок — Section 9 главной спеки.
