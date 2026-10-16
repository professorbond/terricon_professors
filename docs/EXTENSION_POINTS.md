# Бэкенд JanaМен: точки расширения

Как устроен бэкенд и как добавить в него модуль. API для фронтенда описан в [`API_CONTRACT.md`](API_CONTRACT.md).

## Запуск

```sh
docker compose up            # db + backend + frontend: http://localhost:5173, API http://localhost:8000/docs
# или только API локально:
cd backend && uv sync && docker compose up -d db && uv run uvicorn app.main:app --reload
```

Миграции и seed применяются при старте. Сброс демо: `POST /api/demo/reset`.
Swagger со всеми схемами: http://localhost:8000/docs.

## Учётки (пароль у всех `demo1234`)

| login | Роль | Страна | Где | Кто |
|---|---|---|---|---|
| `aigerim` | Employee | KZ | СЦ Алматы · смена Б | Сортировщица; отпуск на согласовании у Ерлана |
| `nurlan` | Employee | KZ | СЦ Алматы · смена Б | 2 отклонённые заявки |
| `asel` | Employee | KZ | СЦ Алматы · смена А | Другая команда (для проверки 403) |
| `erlan` | Manager | KZ | СЦ Алматы · смена Б | Руководитель Айгерим и Нурлана |
| `gulnara` | Manager | KZ | СЦ Алматы · смена А | Руководитель Асель |
| `daniyar` | HRAdmin | KZ | Офис Алматы | HR |
| `bakyt` | Employee | KG | Склад Бишкек | Сотрудник второй страны |
| `aibek` | Manager | KG | Склад Бишкек | Руководитель Бакыта |

## Подключение фронтенда

Все эндпоинты, форматы и расхождения с контрактами фронтенда описаны в [`API_CONTRACT.md`](API_CONTRACT.md).

## Как добавить модуль на бэкенде

Модуль — это пакет `backend/app/modules/<name>/`. Его подключает одна строка в `app/modules/__init__.py::MODULES`.
Эталон — `app/modules/leave/`:

```
modules/leave/
  __init__.py   # module = BackendModule(name="leave", register=register, seed=seed)
  register.py   # регистрирует роутер, тип заявки, подписки на события, тексты i18n
  router.py     # эндпоинты /api/leave/...
  schemas.py    # pydantic-схемы (наследовать ApiModel → camelCase)
  service.py    # бизнес-правила
  seed.py       # тестовые данные модуля
  models.py     # (если нужны свои таблицы) — подхватятся Alembic автоматически
```

```python
def register(ctx: ModuleContext) -> None:
    ctx.i18n({"request.type.vacation": "Отпуск"}, {"request.type.vacation": "Демалыс"})
    ctx.request_types.register(RequestType(code="vacation", number_prefix="JL",
                                           title_key="request.type.vacation", approver="manager"))
    ctx.events.subscribe("request.decided", send_order_to_1c)
    ctx.ticks.register("my_module", on_tick)       # раз в минуту и после demo/advance-time
    ctx.profile.register(contribute_profile)       # свои поля в GET /api/profile/me
    ctx.include_router(router)
```

Модуль с флагом (`BackendModule(..., feature="wage_access")`) подключается, только если фича
есть в `EXT_FEATURES`. Выключенный модуль не регистрирует роуты.

### Тип заявки

Эндпоинт модуля принимает свою форму, валидирует её и вызывает движок:

```python
from app.core.requests import service as requests
req = await requests.create(session, user, "vacation", payload_dict, submission_key)
```

Статусы, история, согласующий (`manager` — руководитель сотрудника, `hr`, `none`), права,
версия, идемпотентность и уведомления движок берёт на себя.
- Системное решение по политике: `requests.decide_by_system(session, id, "Approved", "причина")`.
- Отметка в истории без смены статуса: `requests.add_note(session, req, "event_code", data)`.

### События

| Событие | Аргументы | Для чего |
|---|---|---|
| `request.created` | `session, request, employee` | срок ответа, уведомления |
| `request.before_decision` | `session, request, actor, decision, reason_code, comment, by_system` | **запрет решения** через `raise validation(...)` |
| `request.decided` | `session, request, actor, by_system` | документ в Documentolog, выплата |
| `request.escalated` | `session, request` | уведомления HR |
| `request.cancelled` | `session, request, actor` | — |

Обработчики выполняются в той же транзакции: ошибка в обработчике откатывает всё действие.

### Уведомления

```python
from app.core.notifications import notify
await notify(session, employee_id, "course.assigned", "notif.course.title", "notif.course.body",
             {"course": "Техника безопасности"}, target={"kind": "course", "courseId": cid})
```

Тексты задаются ключами i18n (`ctx.i18n(ru, kk)`) и рендерятся на языке получателя.

### Поля профиля

Модуль добавляет поля в профиль, не трогая модуль `profile`:

```python
async def contribute_profile(session, viewer, employee) -> dict:
    return {"leave_balance": LeaveBalance(...)}   # схемы общих полей — app/core/profile.py
```

### Права

Права проверяются в каждом эндпоинте. UI их только отражает.
- `Depends(rbac.require_role(rbac.MANAGER, rbac.HR))` пропускает только указанные роли.
- `rbac.can_view_employee(user, emp)`, `rbac.is_my_team(manager, emp)`, `rbac.can_view_salary(user, emp)` — проверки доступа к сотруднику.
- `rbac.ensure(cond, "сообщение")` возвращает 403, если условие ложно.
- Чужой объект отдаёт 403 и по прямому id тоже (для уведомлений 404).

### Время, 1С, документы

- Текущее время берётся только через `clock.now()` / `clock.today()`: демо умеет переводить часы.
- 1С:ЗУП только читается: `get_zup().get_hr_attrs / get_salary / get_timesheet / list_recent_offers`.
- Изменения уходят документом: `documentolog.create_document(session, kind, employee_id, data)`.
- Выплата: `bank.send_payout(session, employee_id, amount, reference)` (mock).
- Деньги хранятся как целые тенге (`int`).

### Миграции

```sh
cd backend
docker compose up -d db
uv run alembic revision --autogenerate -m "academy tables"
uv run alembic upgrade head
```

Перед PR подтяни `feature` и проверь, что `uv run alembic heads` показывает одну голову. Если голов
две, поставь в `down_revision` своей миграции последнюю ревизию из `feature`. Чужие миграции не правь.

### Тесты

```sh
cd backend && uv run pytest -q     # SQLite в памяти, docker не нужен
```

Фикстуры `client` и `login("aigerim")` лежат в `tests/conftest.py`.

Сквозная проверка живого API на Postgres (роли, права, сценарии, гонки, демо, CORS — 72 проверки).
Перед демо прогонять обязательно. **Скрипт стирает данные демо** (`/api/demo/reset`):

```sh
docker compose up -d && cd backend && uv run python scripts/smoke_api.py
```

В эндпоинтах берите сессию через `session: AsyncSession = DbSession`: транзакция коммитится
до отправки ответа, и следующий запрос фронта сразу видит изменения.
