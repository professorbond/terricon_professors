# Бэкенд JanaМен: API и точки расширения

Для напарника. Здесь описано, как подключить фронтенд к API (HTTP-адаптер вместо `mocks/`)
и как добавить свой модуль на бэкенде.

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

- Базовый URL: `import.meta.env.VITE_API_URL` (в compose это `http://localhost:8000`). CORS для `:5173` и `:4173` открыт.
- Вход: `POST /api/auth/login {login, password}` → `{accessToken, user}`. Дальше заголовок `Authorization: Bearer <token>`.
  Демо-вход без пароля (аналог выбора роли на `/login`): `POST /api/demo/login-as {login}`, список персонажей: `GET /api/demo/personas`.
- JSON в camelCase. Списки отдаются как `Page<T>`: `{items, nextCursor: null}`.
- Ошибка всегда имеет форму `ServiceProblem` с кодом и HTTP-статусом:
  ```json
  {"kind": "validation", "code": "COMMENT_REQUIRED", "message": "Укажите причину отказа", "fieldErrors": {"comment": ["..."]}, "data": {}}
  ```
  `kind`: `unauthenticated` 401, `forbidden` 403, `not-found` 404, `validation` 422, `conflict` 409.

### Соответствие контрактам `src/services/contracts.ts`

| Контракт фронта | Эндпоинт | Ответ |
|---|---|---|
| `IAuthService.getCurrentUser` | `GET /api/auth/me` | `User` + `country`, `lang` |
| `IAuthService.signInDemo(role)` | `POST /api/demo/login-as {login}` | `{accessToken, user}` |
| `IProfileService.getMyProfile` | `GET /api/profile/me` | `EmployeeProfile` + `role`, `country`, `gradeCode`, `monthlyBase` |
| `ILeaveRequestService.listMine` | `GET /api/leave/requests/my` | `Page<LeaveRequest>` |
| `ILeaveRequestService.getById` | `GET /api/leave/requests/{id}` | `LeaveRequest` |
| `ILeaveRequestService.submit` | `POST /api/leave/requests {submissionKey, startDate, endDate, comment}` | `LeaveRequest` (201) |
| `ILeaveRequestService.listPendingApprovals` | `GET /api/leave/requests/pending` | `Page<LeaveRequest>` |
| `ILeaveRequestService.listTeam` | `GET /api/leave/requests/team` | `Page<LeaveRequest>`, все статусы |
| `ILeaveRequestService.decide` | `POST /api/leave/requests/{id}/decision {decision, expectedVersion, comment, reasonCode?}` | `LeaveRequest` |
| `INotificationService.listMine` | `GET /api/notifications[?unreadOnly=true]` | `Page<Notification>` |
| `INotificationService.markRead` | `POST /api/notifications/{id}/read` | `Notification` |
| счётчик колокольчика | `GET /api/notifications/unread-count` | `{unread}` |

`LeaveRequest` совпадает с моделью фронта, плюс несколько полей:
- `decisionComment`, `decisionReasonCode`, `decidedBySystem`;
- `permissions: {canDecide, canCancel}`: показывать кнопки по ним, а не по роли;
- `event` в каждом элементе `history`: `created | approved | rejected | escalated | cancelled | document_registered`.

**Новый статус `Escalated`** означает, что срок ответа руководителя истёк и заявку передали HR
(это будет делать модуль гарантий). Его нужно добавить в `LeaveStatus` и в бейдж.

Остаток отпуска: `GET /api/leave/balance` → `{days, asOf, pendingDays}`. Он берётся из mock 1С:ЗУП.
Одобренный отпуск уходит приказом в Documentolog, после чего остаток в «1С» уменьшается.

### Другие эндпоинты каркаса

| Что | Эндпоинт | Роли |
|---|---|---|
| Все заявки пользователя (любые типы) | `GET /api/requests/my[?type=]` | все |
| Карточка любой заявки | `GET /api/requests/{id}` | владелец, руководитель команды, HR |
| Очередь согласования (любые типы) | `GET /api/requests/inbox[?status=open\|all&type=]` | Manager, HRAdmin |
| Решение / отзыв | `POST /api/requests/{id}/decide`, `POST /api/requests/{id}/cancel` | согласующий / автор |
| Реестр HR | `GET /api/requests[?type=&status=&country=]` | HRAdmin |
| Типы заявок | `GET /api/requests/types` | все |
| Профиль сотрудника | `GET /api/employees/{id}` | сам, его руководитель (без зарплаты), HR |
| Моя команда | `GET /api/team` | Manager |
| Все сотрудники | `GET /api/employees[?country=]` | HRAdmin |
| Флаги, страна, язык | `GET /api/settings` → `{features, demoMode, country, lang, llmAvailable}` | все |
| Язык ru/kk | `PUT /api/auth/me/lang {lang}` | все |
| Демо | `POST /api/demo/advance-time {hours}`, `POST /api/demo/reset`, `GET /api/demo/state` | только при `DEMO_MODE` |

«Мои заявки» лучше строить на `GET /api/requests/my`. Тогда туда автоматически попадут
и «Зарплата по факту», и обращения Даниила. У каждой заявки есть `type` и `typeTitle`.

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
    ctx.i18n({"request.type.leave": "Отпуск"}, {"request.type.leave": "Демалыс"})
    ctx.request_types.register(RequestType(code="leave", number_prefix="JL",
                                           title_key="request.type.leave", approver="manager"))
    ctx.events.subscribe("request.decided", send_order_to_1c)
    ctx.ticks.register("my_module", on_tick)       # раз в минуту и после demo/advance-time
    ctx.include_router(router)
```

Модуль с флагом (`BackendModule(..., feature="wage_access")`) подключается, только если фича
есть в `EXT_FEATURES`. Выключенный модуль не регистрирует роуты.

### Тип заявки

Эндпоинт модуля принимает свою форму, валидирует её и вызывает движок:

```python
from app.core.requests import service as requests
req = await requests.create(session, user, "leave", payload_dict, submission_key)
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
