"""QA А3: матрица доступа «эндпоинт × роль» (CLAUDE.md §8). Каждая клетка — на свежей базе.

Роли: сотрудник (aigerim), коллега из той же команды (nurlan), руководитель своей команды (erlan),
руководитель чужой команды (gulnara), HR (daniyar), сотрудник другой страны (bakyt).
QA_MATRIX_OUT=путь — записать итоговую таблицу в markdown."""

import os
from datetime import timedelta

import pytest

from app.core import clock

ROLES = {
    "employee": "aigerim",
    "colleague": "nurlan",
    "own_manager": "erlan",
    "other_manager": "gulnara",
    "hr": "daniyar",
    "other_country": "bakyt",
}
FUTURE = str(clock.today() + timedelta(days=9))

# (название, метод, путь (может ссылаться на {pending}/{grievance}/{policy}/{gap}), тело, {роль: код})
E, C, OM, XM, HR, KG = ROLES  # короткие ключи для таблицы ниже
MATRIX = [
    ("Свой профиль", "GET", "/api/profile/me", None, dict.fromkeys(ROLES, 200)),
    ("Профиль Айгерим", "GET", "/api/employees/emp-aigerim", None, {E: 200, C: 403, OM: 200, XM: 403, HR: 200, KG: 403}),
    ("Команда", "GET", "/api/team", None, {E: 403, C: 403, OM: 200, XM: 200, HR: 200, KG: 403}),
    ("Заявка Айгерим (карточка)", "GET", "/api/requests/{pending}", None, {E: 200, C: 403, OM: 200, XM: 403, HR: 200, KG: 403}),
    ("Решение по заявке Айгерим", "POST", "/api/requests/{pending}/decide", {"decision": "Approved"}, {E: 403, C: 403, OM: 200, XM: 403, HR: 403, KG: 403}),
    ("Отзыв заявки Айгерим", "POST", "/api/requests/{pending}/cancel", None, {E: 200, C: 403, OM: 403, XM: 403, HR: 403, KG: 403}),
    ("Входящие", "GET", "/api/requests/inbox", None, {E: 403, C: 403, OM: 200, XM: 200, HR: 200, KG: 403}),
    ("Реестр всех заявок", "GET", "/api/requests/all", None, {E: 403, C: 403, OM: 403, XM: 403, HR: 200, KG: 403}),
    ("Анонимное обращение Айгерим", "GET", "/api/requests/{grievance}", None, {E: 200, C: 403, OM: 403, XM: 403, HR: 200, KG: 403}),
    ("Назначить курс Айгерим", "POST", "/api/academy/assignments", {"employeeId": "emp-aigerim", "courseId": "course-returns"},
     {E: 403, C: 403, OM: 409, XM: 403, HR: 409, KG: 403}),  # 409: курс уже назначен — права пройдены
    ("Назначить курс Нурлану", "POST", "/api/academy/assignments", {"employeeId": "emp-nurlan", "courseId": "course-returns"},
     {E: 403, C: 403, OM: 201, XM: 403, HR: 201, KG: 403}),
    ("Прогресс обучения команды", "GET", "/api/academy/progress", None, {E: 403, C: 403, OM: 200, XM: 200, HR: 200, KG: 403}),
    ("Своя лестница", "GET", "/api/ext/ladder/me", None, dict.fromkeys(ROLES, 200)),
    ("Все грейды и вилки", "GET", "/api/ext/ladder/grades", None, {E: 403, C: 403, OM: 403, XM: 403, HR: 200, KG: 403}),
    ("Своя «Зарплата по факту»", "GET", "/api/ext/wage/summary", None, dict.fromkeys(ROLES, 200)),
    ("Политики своей страны", "GET", "/api/ext/policies", None, dict.fromkeys(ROLES, 200)),
    ("Политики KG", "GET", "/api/ext/policies?country=KG", None, {E: 403, C: 403, OM: 403, XM: 403, HR: 200, KG: 200}),
    ("Изменить политику", "PUT", "/api/ext/policies/{policy}", {"slaHours": 24}, {E: 403, C: 403, OM: 403, XM: 403, HR: 200, KG: 403}),
    ("Радар", "GET", "/api/ext/hr/risks", None, {E: 403, C: 403, OM: 403, XM: 403, HR: 200, KG: 403}),
    ("Счётчик", "GET", "/api/ext/hr/savings", None, {E: 403, C: 403, OM: 403, XM: 403, HR: 200, KG: 403}),
    ("Рентген (все)", "GET", "/api/ext/hr/xray", None, {E: 403, C: 403, OM: 403, XM: 403, HR: 200, KG: 403}),
    ("Рентген (себя)", "GET", "/api/ext/hr/xray/me", None, {E: 403, C: 403, OM: 200, XM: 200, HR: 403, KG: 403}),
    ("Пробелы базы", "GET", "/api/ext/kb/gaps", None, {E: 403, C: 403, OM: 403, XM: 403, HR: 200, KG: 403}),
    ("Черновик правила", "POST", "/api/ext/kb/gaps/{gap}/draft", None, {E: 403, C: 403, OM: 403, XM: 403, HR: 200, KG: 403}),
    ("Опубликовать смену (свой центр)", "POST", "/api/ext/shifts", {"date": FUTURE, "startTime": "08:00", "endTime": "20:00", "payPreview": 12000},
     {E: 403, C: 403, OM: 201, XM: 201, HR: 422, KG: 403}),  # HR без centerId → CENTER_REQUIRED, права пройдены
    ("Смены центра", "GET", "/api/ext/shifts/team", None, {E: 403, C: 403, OM: 200, XM: 200, HR: 200, KG: 403}),
    ("Источник KZ (база знаний)", "GET", "/api/ai/sources/kb-kz-vacation", None, {E: 200, C: 200, OM: 200, XM: 200, HR: 200, KG: 404}),
]

RESULTS: dict[tuple[str, str], tuple[int, int]] = {}


async def resolve(client, login, path: str) -> str:
    if "{" not in path:
        return path
    hd, ha = await login("daniyar"), await login("aigerim")
    ids = {}
    if "{pending}" in path:
        ids["pending"] = (await client.get("/api/requests/my?status=Submitted&type=vacation", headers=ha)).json()["items"][0]["id"]
    if "{grievance}" in path:
        r = await client.post("/api/ext/grievances", headers=ha, json={"category": "other", "text": "Анонимное обращение для теста", "anonymous": True})
        ids["grievance"] = r.json()["id"]
    if "{policy}" in path:
        ids["policy"] = (await client.get("/api/ext/policies", headers=hd)).json()[0]["id"]
    if "{gap}" in path:
        ids["gap"] = (await client.get("/api/ext/kb/gaps", headers=hd)).json()[0]["id"]
    return path.format(**ids)


CASES = [(row, role) for row in MATRIX for role in ROLES]


@pytest.mark.parametrize("row,role", CASES, ids=[f"{r[0]}·{role}" for r, role in CASES])
async def test_access(client, login, row, role):
    name, method, path, body, expected = row
    url = await resolve(client, login, path)
    r = await client.request(method, url, headers=await login(ROLES[role]), json=body)
    RESULTS[(name, role)] = (r.status_code, expected[role])
    assert r.status_code == expected[role], f"{name} / {role}: {r.status_code} {r.text[:200]}"


def test_zz_render_table():
    """Таблица для docs/QA_REPORT.md (после всех клеток)."""
    out = os.environ.get("QA_MATRIX_OUT")
    if not out or not RESULTS:
        pytest.skip("QA_MATRIX_OUT не задан")
    head = "| Ресурс | " + " | ".join(ROLES) + " |\n|---|" + "---|" * len(ROLES) + "\n"
    rows = []
    for name, *_ in MATRIX:
        cells = []
        for role in ROLES:
            got, exp = RESULTS.get((name, role), (0, 0))
            cells.append(f"{got}" + ("" if got == exp else f" ❌ (ждали {exp})"))
        rows.append(f"| {name} | " + " | ".join(cells) + " |")
    open(out, "w", encoding="utf-8").write(head + "\n".join(rows) + "\n")
