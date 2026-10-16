# Ручная проверка в Swagger (15–20 минут)

Откройте http://localhost:8000/docs. Перед началом выполните `POST /api/demo/reset` (без авторизации).

**Как войти за персонажа.** Выполните `POST /api/auth/login` с телом `{"login": "aigerim", "password": "demo1234"}`,
скопируйте `accessToken`, нажмите **Authorize** вверху справа, вставьте токен и нажмите Authorize.
Чтобы сменить персонажа, нажмите Logout и войдите заново.

---

### 1. Профиль: поля кейса и остаток (Айгерим)
`GET /api/profile/me`. Ожидаемый ответ:
- `displayName` = «Айгерим Сейткали», `company` = «Jana Post», `department` = «СЦ Алматы · смена Б»;
- `manager.displayName` = «Ерлан Мухамедов»;
- `leaveBalance` = `{days: 21, pendingDays: 7, availableDays: 14}`;
- в `assignedTraining` два курса, первый `Completed`;
- `monthlyBase` = 240000.

### 2. Руководитель не видит чужого сотрудника (Ерлан)
- `GET /api/employees/{employee_id}` с `emp-asel` → **403**, `code: FORBIDDEN`.
- С `emp-aigerim` → 200, но `monthlyBase: null`: руководитель не видит зарплату.

### 3. Отказ без причины запрещён (Ерлан)
1. `GET /api/leave/pending` → скопируйте `id` заявки Айгерим.
2. `POST /api/requests/{request_id}/decide` с телом `{"decision": "Rejected", "comment": "Не могу отпустить"}` → **422**, `code: REASON_REQUIRED`.
3. Повторите с `"reasonCode": "STAFFING"` и комментарием от 10 символов → 200, `status: Rejected`, `decisionReasonCode: STAFFING`.

### 4. Сквозной путь отпуска и уведомление (Айгерим → Ерлан → Айгерим)
1. Айгерим: `POST /api/leave` с телом `{"submissionKey": "manual-1", "startDate": "<через 60 дней>", "endDate": "<+2 дня>", "comment": ""}` → 201. В `extensions.guarantee.deadlineAt` указан срок ответа.
2. Ерлан: `POST /api/requests/{id}/decide` с телом `{"decision": "Approved"}` → 200.
3. Айгерим: `GET /api/notifications?unreadOnly=true` → «Заявка одобрена». `GET /api/leave/{id}` → в `documents` есть «leave_order», в истории `created → deadline_set → approved → document_registered`.

### 5. «Зарплата по факту» (Айгерим)
1. `GET /api/ext/wage/summary` → `earned: 168000`, `available: 84000`, `shiftsWorked: 14`. Это верно в середине месяца; в первые дни месяца смен меньше.
2. `POST /api/ext/wage/withdraw` с `{"amount": 100000}` → **422** `AMOUNT_EXCEEDS_AVAILABLE`, `data.available: 84000`.
3. `{"amount": 60000}` → 201, `summary.available: 24000`, `documentNumber` вида `DL-…`.

### 6. Гарантия: одобрение по сроку (Айгерим, затем «+2 дня»)
1. Сначала сброс: `POST /api/demo/reset`, затем войдите заново.
2. `POST /api/demo/advance-time` с `{"hours": 48}`.
3. Айгерим: `GET /api/requests/my?status=Approved` → её заявка на отпуск: `decidedBySystem: true`, `extensions.guarantee.resolution: auto_approved`.

### 7. HR видит анонимное обращение без автора (Айгерим → Данияр)
1. Айгерим: `POST /api/ext/grievances` с `{"category": "manager", "text": "Руководитель повышает голос", "anonymous": true}` → 201.
2. Данияр: `GET /api/requests/{id}` → `employeeId: null`, `employeeName: null`, в истории «Анонимный автор». В ответе нигде нет «Айгерим».
3. Ерлан: тот же запрос → **403**.

### 8. Academy: тест без правильных ответов и прогресс (Айгерим)
1. `GET /api/academy/courses/course-safety` → в `questions` есть только `id, ord, text, options`, правильного ответа нет.
2. `POST /api/academy/courses/course-safety/submit` с `{"answers": [1, 1, 1, 0]}` → `passed: true`, `score: 100`.
3. `GET /api/ext/ladder/me` → `remainingCourses: 0`, `ready: true`.

### 9. AI Jana: источник, страна, защита (Айгерим, Бакыт)
- Айгерим: `POST /api/ai/ask` с `{"question": "Сколько дней отпуска положено?"}` → `kind: grounded`, источник `kb-kz-vacation` (ТК РК), в тексте 24 дня.
- Бакыт: тот же вопрос → источник `kb-kg-vacation` (ТК КР), 28 дней.
- Айгерим: «Какая зарплата у моего начальника?» → `kind: no-answer`, `reason: other_person`.
- Айгерим: «Как оплачиваются ночные смены?» → `no-answer`, `escalateAvailable: true`.

### 10. HR-пульт: радар и счётчик (Данияр)
1. `GET /api/ext/hr/risks?country=KZ` → у Айгерим `no_review` и `pay_equity`, у Нурлана `rejections`, `slow_answers` и `open_grievance`.
2. `GET /api/ext/hr/savings` → `saved: 9900000`.
3. Возьмите `id` любого сигнала Айгерим: `POST /api/ext/hr/risks/{signal_id}/confirm-retained`.
4. `GET /api/ext/hr/savings` → `saved: 10800000`.
5. Айгерим или Ерлан: `GET /api/ext/hr/risks` → **403**.

---

Если какой-то шаг не совпал, запишите номер шага и ответ. Автоматически всё это проверяют
`uv run pytest -q` и `uv run python scripts/demo_check.py`.
