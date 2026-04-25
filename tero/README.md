# Tero — твой README

> Главная спека: `../docs/superpowers/specs/2026-04-25-healthcare-best-of-merge.md`
> Контракты Pydantic: `../contracts/schemas.py` (ты их и пишешь в MVP 0)
> Дедлайн: **19 часов** от старта работы (2026-04-25)
> Команда: **3 человека** — Tero, Mian (весь backend + DLT + агенты), Arushi (frontend)

## Что изменилось vs прошлая версия спеки

- **Mubarak больше не в команде.** Mian абсорбировал триаж/intake/dead-zones — у тебя освободились часы.
- **Voice MCP больше не твой основной компонент.** Web Speech API (браузер, Arushi, 15 минут) = primary voice path. Твой Fish Audio + OpenAI Realtime стек = **Layer 4 stretch only**, по умолчанию НЕ строится.
- **Stack boundary:** Databricks теперь только data layer. **Никакого** Mosaic AI Agent Framework / Agent Bricks Supervisor / Knowledge Assistant / Databricks Apps SDK. Ты пишешь FastAPI + Databricks Foundation Model APIs (через `mlflow.deployments` client) — модели хостятся в Databricks, но логика агентов это обычный Python.
- **Genie Code** для RouterAgent → demoted в Layer 4. По умолчанию pandas/SQL ranking.
- **Главные новые компоненты у тебя:** атомарная 4-way Delta транзакция, Synthetic Live Stream, Outcome Loop, Reputation aggregation, Integration. Это твоё ядро.

## Что ты теперь делаешь

7 подпапок. Owner интеграции и demo theatre.

| Подпапка | Компонент | Стек | MVP |
|---|---|---|---|
| `supervisor/` | **BookingAgent** — FastAPI orchestrator + SSE endpoint. Вызывает Triage / TrustScorer / Router / TransferCoord. Через `mlflow.deployments` дёргает Databricks-hosted Llama / Claude. | FastAPI, `mlflow.deployments`, OpenAI function-calling pattern (но через FM API endpoints), SSE | 1-2 |
| `router/` | **RouterAgent** — pandas/SQL ranking над Gold Delta (`databricks-sql-connector`). Trust × Reputation × travel × cost. Genie Code = Layer 4. | Python, pandas, `databricks-sql-connector` | 1 |
| `transfer/` | **TransferCoordinator + Atomic Booking** — единая Delta транзакция на 4 INSERT (bed / ambulance / doctor / drug), rollback на любом сбое. Mock 108/ABDM endpoints на портах 9101/9102. **Операционный killer демо.** | Python, Delta ACID, `databricks-sql-connector`, FastAPI mocks | 2 |
| `sim-stream/` | **Synthetic Live Stream** — Python cron берёт 30 случайных Tier-2 строк, `bed_count += randint(-2, +2)`, append в Delta, broadcast по WebSocket в React. Тик таймится прямо посреди питча. | Python, cron, Delta append, WebSocket | 3 |
| `outcome-loop/` | **Outcome Loop** — симуляция T+2h ping (без реального Twilio), append в `outcome_feedback` Delta, ретроактивная коррекция Trust через SQL UPDATE. Animation contract для playback'а Аруши. | Python, Delta SQL | 3 |
| `reputation/` | **Agent Reputation Score** — простая Delta SQL агрегация `honest / total handshakes` per hospital. Pre-rendered React data → Аруша анимирует. | SQL, Python | 3 |
| `integration/` | **Integration + E2E** — pytest проходит весь путь: voice → 3 cards → Validator demote → Reserve → atomic → outcome ping → reputation tick → NGO. Demo theatre rehearsals. | pytest, demo prep | 3 |

## Воркфлоу по MVP (три demo-able продукта)

### MVP 0 — Setup (H 0-2, 2ч)
- [ ] Databricks **Trial for Work** workspace + perms для всех 3 (region us-east-1 или us-west-2)
- [ ] **Edition validation gates** в `docs/edition-status.md`:
  - `mlflow.deployments.get_deploy_client("databricks").list_endpoints()` — должны быть `databricks-meta-llama-3-3-70b-instruct` И `databricks-claude-opus-4-7` (или эквивалент Claude). **Если нет — fallback на ближайший доступный FM endpoint, в крайнем случае внешний API.**
  - Vector Search storage-optimized index (опционально)
  - DLT scaffold runs end-to-end
  - Apps deploy hello-world (только как backup если Vercel сломается)
- [ ] Скачать `VF_Hackathon_Dataset_India_Large.xlsx` → выписать VF pydantic schema → закоммитить `contracts/schemas.py`
- [ ] Закоммитить `mocks/*_output.json` для каждого cross-folder контракта (Mian и Arushi строят против них в MVP 1)
- [ ] **LOCK demo flow в `docs/demo-script.md`** — second-by-second, после этого момента не меняется
- [ ] FastAPI skeleton в `tero/supervisor/`, hello-world вызов через `mlflow.deployments`

### MVP 1 — Working Loop (H 2-7, 5ч) — demo-able #1
> «Speak Hindi → 3 hospitals → reserve confirms.»

- [ ] `tero/supervisor/` — FastAPI `BookingAgent`: `/recommend` POST endpoint, function-call orchestration (Triage → TrustScorer → Router → 3 cards)
- [ ] `tero/supervisor/sse.py` — **mock SSE** endpoint с canned reasoning tokens (Arushi consumes)
- [ ] `tero/router/` — pandas/SQL ranking из Gold через `databricks-sql-connector`, top 3 по trust × distance × specialty
- [ ] `tero/supervisor/reserve.py` — простой POST `/reserve` → `{confirmed: true, eta: 23}` (БЕЗ Delta транзакции, она в MVP 2)
- [ ] E2E smoke test: `pytest tero/supervisor/test_e2e.py`

### MVP 2 — Atomic + Real SSE (H 7-13, 6ч) — demo-able #2 (RUBRIC-PASS)
> «...Validator catches contradiction. Click any score for source. Reserve → 4 tiles commit atomically.»

- [ ] `tero/transfer/atomic.py` — `book_atomic(hospital_id, factors_required)`: открывает Delta транзакцию, INSERT в 4 таблицы, ROLLBACK на любом fail
- [ ] `tero/transfer/mock_endpoints.py` — fake 108/ABDM на портах 9101/9102 с конфигурируемым success/failure (для демо failure-and-retry)
- [ ] `tero/supervisor/sse_real.py` — **заменить mock SSE на реальный** OpenAI/FM streaming, distinct event types `triage` / `extractor` / `validator` / `router` / `transfer` (Arushi color-codes)
- [ ] `tero/supervisor/reserve.py` upgrade — вызывает `book_atomic`, возвращает реальный `atomic_txn_id` или `rollback_reason`
- [ ] **Demo failure-and-retry script:** Reserve A → drug fail (mock сконфигурирован) → 4 tiles красные → auto-suggest B → commit → 4 tiles зелёные

⚠ **HARD CHECKPOINT @ H 13.** Если MVP 2 не зелёный — **freeze**, полируй MVP 1+2, MVP 3 не стартуем. The One Rule срабатывает здесь.

### MVP 3 — Tier-1/2 + Stream + Outcome + Polish (H 13-19, 6ч) — final
> «...Tier-1 verified live, Tier-2 stream tick, T+2h ping → reputation drops, NGOs use the same map.»

- [ ] `tero/sim-stream/` — Python cron, 30 случайных Tier-2 строк, `bed_count += randint(-2,+2)`, occasional `icu_full=True`, append в Delta, WebSocket → React. **Таймь тик на момент середины питча.**
- [ ] `tero/outcome-loop/` — симуляция T+2h ping (БЕЗ реального Twilio), append в `outcome_feedback` Delta, retro-correct Trust через SQL UPDATE
- [ ] `tero/reputation/` — Delta SQL aggregation `honest / total handshakes`, pre-rendered data → Arushi animation
- [ ] `tero/supervisor/tier_routing.py` — Tier-1 (HAS-AGENT) → IntakeAgent endpoint; Tier-2 → BedPredictor + Synthetic Stream + voice fallback (Mode B = Layer 4, не строим)
- [ ] `tero/integration/` — E2E pytest: voice → cards → demote → Reserve → atomic → outcome → reputation → NGO
- [ ] **Counterfactual opener slide** в `docs/pitch-deck/`: «38 lives changed in 90 days, simulated from research/01»
- [ ] **3 demo rehearsals** на H 17, H 18, H 19 — fix timing/audio
- [ ] **Pre-recorded fallback** для каждого «live» момента (см. Section 12 спеки)

## Что эмитчишь

- `BookingAgent /recommend` → агрегированный response для React (3 cards + trust + reasoning)
- `SSE /sse` → `ReasoningPanel.event` (см. Section 7 спеки) — каждый шаг агента стримится
- `book_atomic` → `TransferCoord.output` — atomic_txn_id + factors_locked + deeplinks (Ola/Uber/108 = secondary buttons)
- `RouterOutput` → ranked list для cards
- `outcome_feedback` append → запускает retro-correction
- `reputation` aggregation → tick анимация

## Что потребляешь (mocks из `contracts/`/`mocks/` в MVP 0-1, реальные после)

- `triage_output.json` (Mian)
- `trust_scorer_output.json` (Mian) — теперь с per-field CI + extractor_confidence + validator_contradiction
- `predictor_output.json` (Mian) — для Tier-2
- `intake_handshake.json` (Mian) — Tier-1 hospitals (mock signature OK)
- `dead_zones.json` (Mian) — для NGO tab у Arushi (ты не трогаешь)

## Stack constraints (важно — изменилось)

- ✅ FastAPI service хостится **вне Databricks** (Render / Fly.io / Railway / ngrok tunnel на демо). Внутри Databricks Apps **не клади** — outbound network restriction может уронить SSE.
- ✅ Все LLM вызовы через `mlflow.deployments.get_deploy_client("databricks")` — модели Databricks-hosted, **никаких внешних API ключей** в primary path. Это даёт «all inference inside the lakehouse» — governance/compliance pitch line.
- ✅ Delta операции через `databricks-sql-connector`. Atomic transaction = критический Databricks-native момент, держи его.
- ❌ **Никакого** Mosaic AI Agent Framework / Agent Bricks Supervisor / Knowledge Assistant / Databricks Apps SDK / Genie Code (Layer 4 only) / Lakehouse Monitoring как live demo (только static screenshot в слайде).

## Demo theatre — твоё ядро

Section 10 спеки: на каждой секунде live демо что-то agentic должно двигаться + Reasoning Panel должен стримить токены. Иерархия «если только одно работает» (Section 10):

1. **Reasoning Panel streaming** — потеряем = потеряем F2 killer
2. **Atomic Booking 4-tile flip** — потеряем = потеряем T killer (твой)
3. **Click-to-source MLflow trace** — Mian'a, но ты wire'ишь
4. **Synthetic Stream tick** — потеряем = демо теряет «live» feel для Tier 2 (твой)
5. **Validator demotion visible** — Mian'a контент, ты дёргаешь

## Risks (твои персональные)

- **SSE из FastAPI на Vercel-hosted React работает ТОЛЬКО если FastAPI достижим из браузера юзера** (не за Databricks-only сетью). Хостинг — Render/Fly.io/Railway или ngrok на демо. **High severity.**
- **Atomic 4-way Delta transaction теряет демо impact без визуализации.** Tile-flip animation должна быть wired до конца MVP 2 (с Arushi).
- Voice MCP Mode B (Fish + OpenAI Realtime) **дропается** в Layer 4. Не возвращайся к нему пока Layer 1-3 не зелёные.
- Reasoning Panel сильно зависит от time-to-first-token < 200ms — pre-warm FM endpoints на H 16, держи cached fallback.
