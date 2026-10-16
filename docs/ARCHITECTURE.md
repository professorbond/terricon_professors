# Архитектура JanaМен

```mermaid
flowchart LR
  subgraph Browser
    FE[React SPA<br/>src/ · напарник]
  end
  subgraph Backend[FastAPI · backend/]
    API[Роутеры /api/*<br/>JWT + RBAC на каждом запросе]
    CORE[core: org · requests engine · notifications · events · ticks · clock]
    MOD[modules: leave · academy · ai_jana · ext_*]
    INT[integrations]
  end
  DB[(PostgreSQL 16)]
  ZUP[[1С:ЗУП]]
  DL[[Documentolog]]
  BANK[[Банк-партнёр]]
  LLM[[Anthropic API]]

  FE -- HTTPS + Bearer JWT --> API
  API --> CORE
  API --> MOD
  MOD -- события / движок заявок --> CORE
  CORE --> DB
  MOD --> INT
  INT -- ZupPort: только чтение --> ZUP
  INT -- create_document --> DL
  DL -. приказ проводится в .-> ZUP
  INT -- send_payout --> BANK
  INT -- complete --> LLM
```

## Места интеграций

| Система | Где в коде | Сейчас | Как подключить настоящую |
|---|---|---|---|
| 1С:ЗУП | `backend/app/integrations/zup/` | `MockZup` читает таблицы `zup_*` из seed | Реализовать `ZupPort` (OData или HTTP-сервис 1С: сотрудники, табель, начисления, остатки отпуска), вернуть её из `get_zup()`. Модули не меняются |
| Documentolog | `backend/app/integrations/documentolog/` | Таблица `documents`, документ сразу «зарегистрирован» | Вызов API Documentolog в `create_document`, статус по webhook |
| Банк | `backend/app/integrations/bank/` | Таблица `payouts`, всегда успех | API банка-партнёра для выплат «Зарплаты по факту» |
| LLM (AI Jana) | `backend/app/integrations/llm/` | Claude (`claude-opus-5-5`, effort `low`, серверный фолбэк при отказе модели). Без ключа или при сбое — экстрактивный режим | `ANTHROPIC_API_KEY` в env, ключ только на сервере |

## Принципы

1. **Официальные кадровые данные только читаются.** Приложение не пишет в `zup_*`.
   Изменения (отпуск, аванс) уходят документом через Documentolog, и 1С проводит его сама.
   В mock остаток отпуска = значение в 1С − приказы `leave_order`.
2. **Права проверяет сервер** на каждом запросе. Пользователь определяется из JWT, `employeeId` и роли из тела запроса не принимаются.
3. **Кадровые решения не принимает AI.** Системные решения (`decide_by_system`) принимаются только по политикам, настроенным HR.
4. **Время берётся из `clock.now()`.** Демо переводит часы, и фоновый тик сразу отрабатывает сроки.
5. **Модули изолированы.** Они общаются через события и движок заявок, а не через внутренности друг друга. Ext-фичи выключаются флагом `EXT_FEATURES`.

## Данные (каркас)

| Таблица | Что |
|---|---|
| `countries`, `units`, `employees` | Оргструктура, роли, страна, руководитель |
| `zup_salaries`, `zup_timesheets`, `zup_hr_attrs`, `zup_hire_offers` | Зеркало 1С:ЗУП (mock, только чтение) |
| `requests`, `request_events` | Движок заявок: тип, статус, payload, версия, история |
| `notifications` | Уведомления (ключи i18n + параметры, рендер на языке получателя) |
| `documents`, `payouts` | Mock Documentolog и банка |
| `demo_state` | Смещение демо-часов |
