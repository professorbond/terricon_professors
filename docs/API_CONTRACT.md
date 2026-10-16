# JanaМен API: контракт для фронтенда

Это живой документ, он обновляется после каждого этапа. Полные схемы лежат в Swagger: `http://localhost:8000/docs`.
Поля и типы совпадают с `src/services/contracts.ts` и `src/features/*/model.ts`. Всё, что от них
отличается, перечислено в разделе [«Расхождения»](#расхождения-с-контрактами-фронтенда).

> **Состояние: весь бэкенд из CLAUDE.md готов** (этапы 1–5): обязательная часть кейса и все ext-фичи, каждая за своим флагом. Чек-лист — [`CASE_CHECKLIST.md`](CASE_CHECKLIST.md).

**Статусы:** ✅ работает · 🟡 заглушка с фиксированным ответом (заголовок `X-Stub: true`), формат финальный · ⏳ будет.

## Общее

- Базовый URL: `VITE_API_URL` (в compose `http://localhost:8000`). CORS открыт для `:5173` и `:4173`.
- Авторизация через заголовок `Authorization: Bearer <accessToken>`. Пользователь всегда определяется из токена, поэтому `employeeId` и роль из тела запроса не принимаются.
- JSON в camelCase. Даты `YYYY-MM-DD`, время в ISO 8601 с зоной (UTC). Деньги — целые числа в валюте страны.
- Списки отдаются как `Page<T> = {items: T[], nextCursor: null}`. Пагинации пока нет.
- Ошибка всегда имеет форму `ServiceProblem` с кодами:
  ```json
  {"kind": "validation", "code": "INVALID_DATES", "message": "Дата начала не может быть в прошлом",
   "messageKey": "errors.INVALID_DATES", "fieldErrors": {"startDate": ["..."]}, "data": {}}
  ```
  | kind | HTTP |
  |---|---|
  | `unauthenticated` | 401 |
  | `forbidden` | 403 |
  | `not-found` | 404 |
  | `validation` | 422 |
  | `conflict` | 409 |
  | `unavailable` | 503 |
- Роли: `Employee | Manager | HRAdmin`.
- Статусы заявок: `Submitted | Approved | Rejected | Escalated | Cancelled`.
- После обновления бэкенда демо-данные пересоздаются сами, если поменялся seed. Вручную — `POST /api/demo/reset`.
- Учётки (пароль `demo1234`):
  | login | Роль | Страна | Кто |
  |---|---|---|---|
  | `aigerim` | Employee | KZ | основной персонаж демо |
  | `nurlan` | Employee | KZ | — |
  | `asel` | Employee | KZ | другая команда |
  | `erlan` | Manager | KZ | Айгерим и Нурлан |
  | `gulnara` | Manager | KZ | Асель |
  | `daniyar` | HRAdmin | KZ | — |
  | `bakyt` | Employee | KG | — |
  | `aibek` | Manager | KG | Бакыт |

---

## Вход и сессия — `IAuthService`

| ✅ | Метод | Путь | Роли | Запрос → Ответ |
|---|---|---|---|---|
| ✅ | POST | `/api/auth/login` | все | `{login, password}` → `{accessToken, tokenType, user: User}` |
| ✅ | GET | `/api/auth/me` | все | → `User {id, displayName, role, country, lang}`. Для `getSession`: `employeeId = id` |
| ✅ | PUT | `/api/auth/me/lang` | все | `{lang: "ru"\|"kk"}` → `User` |
| ✅ | POST | `/api/demo/login-as` | демо | `{role: "Employee"\|"Manager"\|"HRAdmin"}` или `{login}` → как `/login`. Для `signInDemo(role)`: Employee → aigerim, Manager → erlan, HRAdmin → daniyar |
| — | — | `signOut` | — | Сервер не нужен: токен без состояния, фронт его просто удаляет |

Ошибки: `INVALID_CREDENTIALS` (401), `UNAUTHENTICATED` (401, нет токена или он истёк).

## Профиль — `IProfileService`

| ✅ | Метод | Путь | Роли | Ответ |
|---|---|---|---|---|
| ✅ | GET | `/api/profile/me` | все | `EmployeeProfile` |
| ✅ | GET | `/api/team?unitId=&country=` | Manager (своя команда), HRAdmin (все, фильтры) | `Page<EmployeeProfile>` |
| ✅ | GET | `/api/employees/{id}` | сам; руководитель своей команды; HR | `EmployeeProfile`. Чужая команда → 403 |

```ts
EmployeeProfile = {
  id, displayName, company, position, department, manager: {id, displayName} | null, hiredOn,
  leaveBalance: { days, asOf, pendingDays, availableDays },   // days = остаток 1С − одобренные; available = days − на рассмотрении
  role, country, lang, unitId, unitKind, qualification, gradeCode,
  monthlyBase: number | null,          // только сам и HR, руководителю null
  assignedTraining: { courseId, title, status, lessonsPercent, scorePercent, dueDate }[],
  unreadNotifications: number
}
```

Изменять официальные поля нельзя: таких эндпоинтов нет. Менять можно только язык.

## Отпуск — `ILeaveRequestService` (тип заявки `vacation`)

| ✅ | Метод | Путь | Роли | Запрос → Ответ |
|---|---|---|---|---|
| ✅ | POST | `/api/leave` | все | `SubmitLeaveInput {submissionKey, startDate, endDate, comment}` → `LeaveRequest` (201). Повтор с тем же `submissionKey` вернёт ту же заявку |
| ✅ | GET | `/api/leave/my` | все | `Page<LeaveRequest>` (`listMine`) |
| ✅ | GET | `/api/leave/pending` | Manager, HRAdmin | Открытые, где пользователь согласующий (`listPendingApprovals`) |
| ✅ | GET | `/api/leave/team` | Manager (своя команда), HRAdmin (все) | Все статусы (`listTeam`) |
| ✅ | GET | `/api/leave/balance` | все | `{days, asOf, pendingDays, availableDays}` |
| ✅ | GET | `/api/leave/{id}` | владелец, руководитель команды, HR | `LeaveRequest` (`getById`) |
| ✅ | POST | `/api/leave/{id}/decision` | согласующий | `LeaveDecision {decision, expectedVersion, comment?, reasonCode?}` → `LeaveRequest` (`decide`) |

```ts
LeaveRequest = {
  id, number /* JL-2026-0001 */, type: "Leave", submissionKey, employeeId, employeeName, managerId, managerName,
  startDate, endDate, requestedDays, comment, status, createdAt, version,
  history: { id, status, occurredAt, actorLabel, actorId /* "system" для системных событий */, comment, event }[],
  // расширение:
  decisionComment, decisionReasonCode, decidedBySystem,
  documents: { id, kind, number }[],      // «Приказ на отпуск» после одобрения
  permissions: { canDecide, canCancel }   // показывать кнопки по ним, а не по роли
}
```

| Ошибка | Код | HTTP | Когда |
|---|---|---|---|
| Неверные даты | `INVALID_DATES` | 422 | Начало в прошлом или конец раньше начала; `fieldErrors.startDate` или `endDate` |
| Не хватает дней | `INSUFFICIENT_BALANCE` | 422 | `data.available` — сколько доступно |
| Пересечение | `OVERLAP` | 409 | Пересекается с заявкой на рассмотрении или одобренной; `data.number` |
| Нет причины отказа | `COMMENT_REQUIRED` | 422 | Отказ без комментария |
| Устаревшая версия | `STALE_VERSION` | 409 | `data.version` — текущая версия |
| Уже решено | `ALREADY_DECIDED` | 409 | Повторное решение |
| Нет прав | `FORBIDDEN` | 403 | Чужая команда или своя заявка |

`history[].event`: `created | approved | rejected | escalated | cancelled | document_registered`.

## Заявки любых типов («Мои заявки», «Входящие», реестр HR)

Здесь лежат все заявки: отпуск, вопрос к HR, позже «Зарплата по факту». «Мои заявки» лучше строить на этом API.

| ✅ | Метод | Путь | Роли | Ответ |
|---|---|---|---|---|
| ✅ | GET | `/api/requests/my?type=&status=` | все | `Page<RequestOut>` |
| ✅ | GET | `/api/requests/inbox?status=open\|all&type=` | Manager: своя команда; HRAdmin: адресованные HR и переданные HR | `Page<RequestOut>` |
| ✅ | GET | `/api/requests/all?type=&status=&unitId=&country=&from=&to=` | HRAdmin | `Page<RequestOut>`. `from`/`to` — дата создания |
| ✅ | GET | `/api/requests/types` | все | `{code, title, approver, cancellable}[]` |
| ✅ | GET | `/api/requests/{id}` | владелец, руководитель команды, HR | `RequestOut` |
| ✅ | POST | `/api/requests/{id}/decide` | согласующий | `{decision, expectedVersion?, reasonCode?, comment?}` → `RequestOut` |
| ✅ | POST | `/api/requests/{id}/cancel` | автор, пока `Submitted` | `RequestOut` |

```ts
RequestOut = { id, number, type /* vacation | hr_question | … */, typeTitle, status, employeeId, employeeName,
  approverKind /* manager | hr | none */, approverId, approverName, payload, submissionKey, createdAt, decidedAt,
  decidedBySystem, decisionReasonCode, decisionComment, version, history[], documents[], permissions }
```

## Вопрос к HR (тип `hr_question`)

| ✅ | Метод | Путь | Роли | Запрос → Ответ |
|---|---|---|---|---|
| ✅ | POST | `/api/hr-questions` | все | `{question, aiContext?}` → `RequestOut` (201), уведомление HR |

HR отвечает через `POST /api/requests/{id}/decide {decision: "Approved", comment: "<ответ>"}`. Комментарий
обязателен: `COMMENT_REQUIRED`. Автор получает уведомление с ответом. Кнопка «Спросить HR» в AI Jana вызывает этот эндпоинт.

## Уведомления — `INotificationService`

| ✅ | Метод | Путь | Ответ |
|---|---|---|---|
| ✅ | GET | `/api/notifications?unreadOnly=true` | `Page<Notification>` (`listMine`) |
| ✅ | GET | `/api/notifications/unread-count` | `{unread}` |
| ✅ | POST | `/api/notifications/{id}/read` | `Notification` (`markRead`); чужое → 404 |
| ✅ | POST | `/api/notifications/read-all` | `{unread: 0}` |

```ts
Notification = { id, userId, title, message, createdAt, readAt, target: {kind:"request",requestId} | {kind:"course",courseId} | null,
  // расширение: ключи i18n, чтобы фронт мог перевести сам
  kind, titleKey, bodyKey, params, link }
```

`kind`:
- `request.created` — согласующему;
- `request.decided` — автору;
- `request.escalated`;
- `academy.assigned`;
- `academy.completed`.

`title` и `message` уже переведены на язык пользователя (`lang`).

## Jana Academy — `AcademyService` ✅

| | Метод | Путь | Роли | Ответ |
|---|---|---|---|---|
| ✅ | GET | `/api/academy/courses` | все | `Page<CourseSummary>` — каталог |
| ✅ | GET | `/api/academy/my` | все | `Page<AssignedCourse>` (`listAssigned`) = `CourseSummary` + `{assignedAt, dueDate, progress}` |
| ✅ | GET | `/api/academy/courses/{id}` | все | `CourseDetail` = `CourseSummary` + `{passingScore, assigned, lessons[{id, ord, title, contentMd, completed}], questions[{id, ord, text, options[]}], progress}`. **Правильных ответов в нём нет** |
| ✅ | GET | `/api/academy/courses/{id}/progress` | все | `CourseProgress` (`getProgress`) |
| ✅ | POST | `/api/academy/lessons/{lessonId}/complete` | все | `CourseProgress` (`completeLesson`: `courseId` в пути не нужен) |
| ✅ | POST | `/api/academy/courses/{id}/submit` | все | `{answers: number[]}` → `{score, passed, passingScore, correct, total, progress}` |
| ✅ | POST | `/api/academy/assignments` | Manager (своей команде), HRAdmin | `{employeeId, courseId, dueDate?}` → `Assignment` (201) |
| ✅ | GET | `/api/academy/progress?unitId=` | Manager (своя команда), HRAdmin | `Page<{employeeId, employeeName, unitId, courseId, courseTitle, dueDate, progress}>` |

| Ошибка | Код | HTTP |
|---|---|---|
| Ответов меньше или больше, чем вопросов | `ANSWERS_MISMATCH` (`data.total`) | 422 |
| Курс уже назначен | `ALREADY_ASSIGNED` | 409 |
| Срок в прошлом | `INVALID_DATES` | 422 |
| Назначение чужой команде | `FORBIDDEN` | 403 |
| Курс или урок не найден либо из другой страны | `NOT_FOUND` | 404 |

Статусы курса:
- `Assigned` — ещё не начат;
- `InProgress` — пройден хотя бы один урок или была попытка теста;
- `Completed` — тест сдан (`score ≥ passingScore`).

Пересдавать можно, в зачёт идёт лучший результат. При первой успешной сдаче приходит уведомление `academy.completed`
и публикуется событие `academy.course_completed` для лестницы. Назначение курса отправляет уведомление `academy.assigned`
с `target {kind: "course", courseId}`. Названия курсов приходят на языке пользователя (ru/kk).

Seed: «Работа с возвратами» (`course-returns`, 3 урока, 3 вопроса) и «Техника безопасности на сортировке»
(`course-safety`, 4 урока, 4 вопроса). Оба назначены Айгерим, первый уже пройден.

```ts
CourseProgress = { courseId, completedLessonIds, totalLessons, status: "Assigned"|"InProgress"|"Completed",
                   scorePercent, passed, lessonsPercent }
```

## AI Jana — `AssistantService` ✅

| | Метод | Путь | Ответ |
|---|---|---|---|
| ✅ | POST | `/api/ai/ask` | `{question, lang?}` → `AskOut` |
| ✅ | GET | `/api/ai/sources/{articleId}` | `KnowledgeArticle {id, title, body, updatedAt, country, sourceLabel}` (`getSource`) |

```ts
AskOut = {
  kind: "grounded" | "no-answer",                  // = AssistantAnswer фронтенда
  text: string | null,                             // grounded
  message: string | null,                          // no-answer
  sources: { articleId, title, section, updatedAt, sourceLabel }[],   // у grounded минимум один
  escalation: "HR" | null,
  answer, answered, escalateAvailable,             // формат CLAUDE.md
  reason: "no_match" | "other_person_data" | null
}
```

Как формируется ответ:
1. **Защита.** На вопрос о данных другого человека («зарплата начальника», «больничные Нурлана») приходит отказ без поиска: `reason: "other_person"`, `escalateAvailable: false`.
2. **Свои данные.** На вопросы «сколько у меня отпуска» и «мой оклад» ответ берётся из 1С:ЗУП текущего пользователя. Источник — `articleId: "zup-own-data"`.
3. **Поиск.** BM25 **только по базе страны пользователя** (KZ/KG). Если уверенность ниже порога (0.5), приходит честный отказ: `reason: "no_match"`, `escalation: "HR"`, `escalateAvailable: true`. По кнопке «Спросить HR» вызывается `POST /api/hr-questions`.
4. **Ответ.** С `ANTHROPIC_API_KEY` модель отвечает строго по найденным фрагментам, со ссылками `[Документ, раздел]`. Без ключа или при сбое API отдаётся лучший фрагмент базы. Ответа без источника не бывает.

`lang` (`ru` | `kk`) по умолчанию берётся из языка пользователя. Без LLM ответ даётся на языке базы (русском), сообщения об отказе — на `kk`.
Вопросы записываются в журнал без идентификатора сотрудника. Отсюда HR потом увидит пробелы базы.

## Ext-фичи (этапы 4–5)

Каждая ext-фича выключается флагом `EXT_FEATURES`: выключенная не регистрирует роуты и не добавляет поля.
Список включённых фич отдаёт `GET /api/settings → features[]`. Экраны ext-фич пока не сделаны, здесь только API.

### Гарантии и политики — флаг `guarantees` ✅

| | Метод | Путь | Роли | Ответ |
|---|---|---|---|---|
| ✅ | GET | `/api/ext/guarantees/reasons?type=vacation` | все | `{code, title}[]` — справочник для окна отказа |
| ✅ | GET | `/api/ext/guarantees/summary/me` | все | `{openRequests[{requestId, number, type, typeTitle, deadlineAt}], rejectionsWithoutReason, decidedOnTime, decidedTotal, nextSalaryReview}` — блок «Мои гарантии» |
| ✅ | GET | `/api/ext/policies?country=` | все (своя страна), HR — любая | `Policy[]` |
| ✅ | PUT | `/api/ext/policies/{id}` | HRAdmin | Частичное обновление `{slaHours, onTimeout, enabled, wageLimitPct, …}` |

- **Срок ответа.** При создании заявки, если у страны есть политика для этого типа, в карточке заявки
  (`RequestOut` и `LeaveRequest`) появляется `extensions.guarantee = {deadlineAt, resolution, overdue, decidedLate}`.
  `resolution` принимает значения `none | auto_approved | escalated | overdue`. В истории появляется событие `deadline_set`,
  автор получает уведомление `guarantee.deadline`.
- **Истёк срок.** По политике заявка одобряется системой (`decidedBySystem: true`, `actorId: "system"`) или передаётся HR (статус `Escalated`).
  Если заявка уже адресована HR, ставится `resolution: overdue` и HR получает уведомление `guarantee.overdue`.
- **Отказ только с причиной** (для всех типов заявок). Нужны `reasonCode` из справочника и `comment` не короче 10 символов. Ошибки:
  - `REASON_REQUIRED` — нет кода;
  - `UNKNOWN_REASON` — кода нет в справочнике, в `data.allowed` список допустимых;
  - `COMMENT_REQUIRED` — комментарий короче 10 символов.

  ⚠️ **Нужна правка фронтенда:** в окне отказа должен быть выбор причины (`GET /api/ext/guarantees/reasons?type=…`),
  а выбранный код отправляется в `reasonCode`. Пока его нет, можно поставить `GUARANTEES_REQUIRE_REASON=false`:
  тогда без кода подставится `OTHER`, но комментарий от 10 символов всё равно обязателен.
- **Деньги.** Для денежных типов автоодобрение по сроку запрещено: `AUTO_APPROVE_FORBIDDEN`.
- **Политики по странам.** KZ: отпуск 48 ч с автоодобрением, вопрос к HR 72 ч. KG: отпуск 72 ч.

### «Зарплата по факту» — флаг `wage_access` ✅

Заменяет «Аванс» из кейса: тип заявки `wage_access`, без согласующего. В «Моих заявках» она появляется автоматически.

| | Метод | Путь | Роли | Ответ |
|---|---|---|---|---|
| ✅ | GET | `/api/ext/wage/summary` | все (только своё) | `{period, currency, shiftsWorked, nightShifts, shiftsPlanned, earned, limitPct, withdrawn, available, withdrawalsLeft, minAmount, maxPerPeriod}` |
| ✅ | POST | `/api/ext/wage/withdraw` | все | `{amount}` → `{requestId, requestNumber, amount, documentNumber, payoutId, summary}` (201) |
| ✅ | GET | `/api/ext/wage/payslip-explained?period=YYYY-MM` | все | `{lines[{code, label, amount}], gross, net, alreadyReceived, toBePaid, note}` — расчётка «смены + ночные − ОПВ − ВОСМС − ИПН» |

- **Расчёт.** Заработано = смены из табеля 1С × ставка за смену + ночные доплаты. Доступно = заработано × лимит страны (KZ 50%, KG 40%) − уже полученное в этом месяце.
- **Вывод в три шага:** экран «Доступно сейчас», ввод суммы, подтверждение. Дальше система сама:
  1. создаёт заявку `wage_access` и одобряет её (`decidedBySystem`);
  2. оформляет документ «Аванс по заявлению» в Documentolog;
  3. отправляет выплату через банк (mock);
  4. присылает уведомление `wage.paid` «Деньги отправлены».

  Руководитель в процессе не участвует.
- **Ошибки:**

  | Код | Когда | `data` |
  |---|---|---|
  | `AMOUNT_EXCEEDS_AVAILABLE` | Сумма больше доступной | `available` |
  | `BELOW_MIN_AMOUNT` | Сумма меньше минимальной | `minAmount` |
  | `LIMIT_PER_PERIOD` | Превышено число выводов за месяц | `maxPerPeriod` |
  | `INVALID_PERIOD` | Неверный формат периода | — |
- **Профиль.** `GET /api/profile/me → extensions.wageAccess` содержит ту же сводку для виджета на главной. Показывается только самому сотруднику.
- **AI Jana.** На вопрос «сколько я могу снять по факту?» отвечает этой суммой с источником «Данные 1С:ЗУП».
- Ставки удержаний в расчётке демонстрационные, это прописано в `note`.

### «Открытая лестница» — флаг `ladder` ✅

| | Метод | Путь | Роли | Ответ |
|---|---|---|---|---|
| ✅ | GET | `/api/ext/ladder/me` | все (только своё) | `{current, next, criteria[{kind, title, done, courseId?, required?, actual?}], criteriaDone, criteriaTotal, remainingCourses, raiseToNextMin, nextReviewDate, ready}` |
| ✅ | GET | `/api/ext/ladder/course-tags` | все | `{courseId, grades[{code, title}]}[]` для бейджа «Нужен для грейда SORT-2» в Academy. Вилки обнулены |
| ✅ | GET | `/api/ext/ladder/grades?country=` | HRAdmin | Все грейды с вилками |

- `current` и `next` имеют вид `{code, title, bandMin, bandMax, currency}`. Сотрудник видит **только свой и следующий** грейд. Зарплаты других людей не возвращаются никогда.
- `raiseToNextMin` = нижняя граница следующего грейда − собственный оклад. У Айгерим это +35 000 ₸.
- Критерии бывают трёх видов: `course` (из Academy), `months_in_grade` и `no_incidents` (из 1С:ЗУП).
- После сдачи курса, который входит в критерии, приходит уведомление: `ladder.criterion` («Выполнено N из M») или `ladder.ready` («Все условия выполнены»).
- `nextReviewDate` — дата пересмотра, предложенного радаром. Если пересмотр не предложен, это дата последнего пересмотра плюс период страны.
- В профиле лестница лежит в `extensions.ladder` и видна только самому сотруднику.

### «Обращение» — флаг `grievance` ✅

| | Метод | Путь | Роли | Запрос → ответ |
|---|---|---|---|---|
| ✅ | POST | `/api/ext/grievances` | все | `{category: safety\|pay\|manager\|conditions\|discrimination\|other, text, anonymous}` → `RequestOut` (201) |

- Тип заявки `grievance`. Согласующий — HR (не руководитель). Срок ответа по политике — 72 ч; если HR не ответил вовремя, ставится `overdue`.
- HR решает через `POST /api/requests/{id}/decide` с обязательным комментарием (ответом). Автор получает уведомление «Ответ на обращение».
- **Анонимное обращение.** У всех, кроме автора, `employeeId` и `employeeName` равны `null`, а в истории стоит «Анонимный автор».
  Фильтр реестра по подразделению анонимные обращения не показывает, радар не связывает их с человеком.
- Руководитель обращений не видит вообще: 403 по id, во входящих их нет.
- В прототипе автор хранится в БД, чтобы видеть ответ. Это указано в README.

### Рентген руководителей — флаг `xray` ✅

Это аналитика HR-процессов, а не оценка эффективности людей. Окно — 90 дней, учитываются заявки, где руководитель — согласующий.

| | Метод | Путь | Роли | Ответ |
|---|---|---|---|---|
| ✅ | GET | `/api/ext/hr/xray?country=` | HRAdmin | `Page<{managerId, managerName, department, country, teamSize, decided, medianResponseHours, rejectionShare, lateDecisions, pendingNow, teamAtRisk}>`. Первыми идут руководители с наибольшим числом решений позже срока |
| ✅ | GET | `/api/ext/hr/xray/me` | Manager | `{metrics, peers, slowerThanPct, lateRank}` — «вы отвечаете медленнее X% коллег». Чужих имён и цифр в ответе нет |

Сотрудник получает 403. В seed Ерлан наверху: 3 решения позже срока, Гульнара отвечает быстро.

### Пробелы базы знаний — флаг `kb_gaps` ✅ (только HRAdmin)

| | Метод | Путь | Ответ |
|---|---|---|---|
| ✅ | GET | `/api/ext/kb/gaps?country=` | `{id, country, label, count, samples[], status: open\|drafted\|published, draftDocId, lastAskedAt}[]` — «23 вопроса: как оплачиваются ночные смены (KZ)» |
| ✅ | POST | `/api/ext/kb/gaps/{id}/draft` | `Doc`. Черновик правила: с LLM — по вопросам сотрудников, цифры заменены на [указать]; без LLM — шаблон |
| ✅ | GET | `/api/ext/kb/docs/{id}` | `Doc {id, country, title, sourceLabel, bodyMd, status, updatedAt}` |
| ✅ | PUT | `/api/ext/kb/docs/{id}` | `{title?, sourceLabel?, bodyMd?}` — правка черновика; опубликованный → 409 `NOT_A_DRAFT` |
| ✅ | POST | `/api/ext/kb/docs/{id}/publish` | Публикует HR: документ попадает в базу страны, AI начинает отвечать с источником «Внутреннее правило…» |

- Вопросы без ответа группируются автоматически: стемминг, TF-IDF по словам, которых нет в базе страны, косинус ≥ 0.5.
- В API нет имён и идентификаторов тех, кто спрашивал.
- AI ничего не публикует сам: черновик всегда утверждает человек.
- В seed: 23 вопроса про ночные смены, 6 про больничный и 4 про спецодежду (KZ).

### Биржа смен (мини) — флаг `shifts` ✅

| | Метод | Путь | Роли | Ответ |
|---|---|---|---|---|
| ✅ | GET | `/api/ext/shifts/my` | все | `Page<Shift>` — свои будущие смены |
| ✅ | GET | `/api/ext/shifts/available` | все | `Page<Shift>`: только те смены, которые пользователь может взять сейчас (все проверки пройдены) |
| ✅ | POST | `/api/ext/shifts/{id}/offer` | владелец смены | «Отдать смену», статус → `offered` |
| ✅ | POST | `/api/ext/shifts/{id}/cancel-offer` | владелец | Вернуть смену себе |
| ✅ | POST | `/api/ext/shifts/{id}/take` | все | Взять в одно нажатие, статус → `taken`. Оба участника получают уведомления (`shift.taken`, `shift.given`) |
| ✅ | POST | `/api/ext/shifts` | Manager (свой центр), HRAdmin (`centerId` обязателен) | `{date, startTime, endTime, qualification, payPreview, centerId?}` — открытая смена на пик (201) |
| ✅ | GET | `/api/ext/shifts/team` | Manager (свой центр), HRAdmin | Смены с историей обменов. Руководитель видит, но не согласует |

```ts
Shift = { id, centerId, centerName, date, startTime, endTime, qualification,
          status: "assigned"|"offered"|"open"|"taken", assigneeId, assigneeName,
          payPreview /* «+12 000 ₸» для текущего пользователя */, mine, version }
```

| Ошибка | Код | HTTP |
|---|---|---|
| Квалификация не подходит | `QUALIFICATION_MISMATCH` | 422 |
| Пересечение со своей сменой | `SHIFT_OVERLAP` | 422 |
| Смена уже началась или прошла | `SHIFT_IN_PAST` | 422 |
| Смену уже взяли | `SHIFT_NOT_AVAILABLE` | 409 |
| Другой центр | `FORBIDDEN` | 403 |

Если двое берут одну смену одновременно, побеждает один (блокировка строки).
В seed у Айгерим смены на +1, +3 и +5 день, у Асель на +2, +4 и +6 день, плюс открытая смена на +7 день за 12 000 ₸.

### HR-пульт: радар удержания и счётчик — флаг `hr_console` ✅ (только HRAdmin)

| | Метод | Путь | Ответ |
|---|---|---|---|
| ✅ | GET | `/api/ext/hr/risks?country=` | `Page<RiskCard>`: `{employeeId, employeeName, position, department, country, managerName, openSignals, nextReviewDate, signals[{id, kind, title, details, detectedAt, status, action, actionedAt, retainedConfirmed}]}` |
| ✅ | POST | `/api/ext/hr/risks/{signalId}/propose-review` | `RiskCard`. Пересмотр через 14 дней, сотрудник получает уведомление `salary.review`, сигнал получает статус `actioned` |
| ✅ | POST | `/api/ext/hr/risks/{signalId}/confirm-retained` | `Signal` («Сотрудник остался») — учитывается в счётчике |
| ✅ | POST | `/api/ext/hr/risks/recalculate` | Пересчитать сейчас (то же делает тик раз в минуту) |
| ✅ | GET | `/api/ext/hr/savings?country=` | `{retainedCount, perPerson, saved, currency, formula}` — «Радар сохранил 12 сотрудников = 10,8 млн ₸» |

Сотрудник и руководитель получают 403.

Сигналы (`kind`), `title` уже написан человеческим языком на `ru`/`kk`:

| `kind` | Условие |
|---|---|
| `no_review` | Давно нет пересмотра зарплаты |
| `rejections` | 2 и больше отказов за полгода |
| `pay_equity` | Новичку предложили больше, чем получает сотрудник |
| `slow_answers` | 2 и больше заявок решены позже срока |
| `open_grievance` | Вопрос к HR или обращение без ответа дольше срока |

Радар **не читает** выводы «Зарплаты по факту», вопросы к AI и поведенческие данные, это проверяется тестом.
Seed:
- в зоне риска Айгерим (`no_review`, `pay_equity`), Нурлан (`rejections`, `slow_answers`, `open_grievance`, `pay_equity`) и Асель (`pay_equity`);
- 11 человек уже «сохранены», поэтому счётчик стартует с 9 900 000 ₸ и после демо становится 10 800 000 ₸.

## Настройки и демо

| ✅ | Метод | Путь | Ответ |
|---|---|---|---|
| ✅ | GET | `/api/settings` | `{features[], demoMode, country, lang, llmAvailable}` |
| ✅ | GET | `/api/health` | `{status}` |
| ✅ | GET | `/api/demo/personas` | `{login, displayName, role, country, position}[]` |
| ✅ | GET | `/api/demo/state` | `{now, offsetHours}` |
| ✅ | POST | `/api/demo/advance-time` | `{hours}` → сдвиг часов и тик сроков |
| ✅ | POST | `/api/demo/reset` | Стереть данные и применить seed |

---

## Расхождения с контрактами фронтенда

| # | Где | Фронтенд | Бэкенд | Нужна правка во фронте? |
|---|---|---|---|---|
| 1 | Статусы | `LeaveStatus` без `Escalated` | Есть `Escalated` (передано HR по сроку) | Да, когда подключим гарантии (этап 4). Для отпуска в KZ политика `auto_approve`, поэтому в демо `Escalated` у отпуска не появляется |
| 2 | Остаток | Submitted не резервирует дни | `days` считается так же; дополнительно отдаются `pendingDays` и `availableDays`, и новая заявка проверяется по `availableDays` (CLAUDE.md §5.1) | Нет, `days` совместим |
| 3 | `listAssigned` | `Page<CourseSummary>` | `Page<AssignedCourse>`, расширение `CourseSummary` | Нет |
| 4 | `completeLesson(courseId, lessonId)` | два id | Путь только с `lessonId` | Нет, адаптер просто не передаёт `courseId` |
| 5 | `AssistantAnswer` | `kind/text/message/escalation` | То же плюс поля CLAUDE.md | Нет |
| 6 | `Notification` | `title/message` | То же, уже переведено, плюс ключи i18n | Нет |
| 7 | `LeaveRequestEvent.actorId` | `string` | `"system"` для системных событий | Нет |
| 8 | Имена из CLAUDE.md | — | Взяты имена фронтенда: роли `Employee/Manager/HRAdmin` вместо `employee/manager/hr`, статусы `Submitted…` вместо `pending…`, поля `startDate/endDate` вместо `date_from/date_to` | Нет |
| 9 | `signOut` | метод сервиса | Эндпоинта нет: JWT без состояния | Нет |
| 10 | Отказ по заявке | `LeaveDecision {decision, expectedVersion, comment}` | С гарантиями обязателен `reasonCode` из справочника, комментарий от 10 символов | **Да**: выбор причины в окне отказа. Временный обход — `GUARANTEES_REQUIRE_REASON=false` |
| 11 | Карточка заявки | — | Поле `extensions` (`guarantee` и др.) | Нет; нужно только для бейджа «Ответ до …» |
| 12 | `Notification.target` | Обязательный `{kind: request\|course}` | `null` у уведомлений без объекта: `salary.review` (пересмотр зарплаты), `shift.taken` и `shift.given` (смены). Обязательная часть кейса всегда с `target` | Только для ext-фич: сделать `target` необязательным |
