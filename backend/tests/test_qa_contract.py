"""QA А2: форма ответов совпадает с типами фронтенда напарника (src/features/*/model.ts, src/services/contracts.ts).

Поля типа — обязательное подмножество ответа (бэкенд может добавлять расширения). Даты — ISO.
Набор полей берётся прямо из TypeScript-файлов напарника, чтобы тест ловил расхождение после правок фронта."""

import re
from datetime import date
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
PERSONAS = ["aigerim", "nurlan", "asel", "erlan", "gulnara", "daniyar", "bakyt", "aibek"]


def ts_fields(rel: str, name: str) -> set[str]:
    """Поля interface/type из TS-файла напарника (верхний уровень)."""
    src = (ROOT / rel).read_text(encoding="utf-8")
    m = re.search(rf"(?:interface {name}\b[^{{]*|type {name}\b[^{{]*=[^{{]*)\{{(.*?)\n\}}", src, re.S)
    assert m, f"{name} не найден в {rel}"
    body, depth, top = m.group(1), 0, []
    for line in body.splitlines():
        if depth == 0:
            fm = re.match(r"\s*readonly (\w+)\??:", line)
            if fm:
                top.append(fm.group(1))
        depth += line.count("{") - line.count("}")
    return set(top)


def is_iso_datetime(v: str) -> bool:
    return isinstance(v, str) and bool(re.match(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}", v)) and (v.endswith("Z") or "+" in v[10:])


def is_iso_date(v: str) -> bool:
    try:
        return isinstance(v, str) and date.fromisoformat(v).isoformat() == v
    except ValueError:
        return False


def test_ts_parser_reads_partner_types():
    assert ts_fields("src/features/leave/model.ts", "LeaveRequest") >= {"id", "number", "startDate", "history", "version"}


@pytest.mark.parametrize("login_name", PERSONAS)
async def test_shapes_for_every_persona(client, login, login_name):
    h = await login(login_name)
    user = (await client.get("/api/auth/me", headers=h)).json()
    assert ts_fields("src/features/identity/model.ts", "User") <= set(user)
    assert user["role"] in {"Employee", "Manager", "HRAdmin"}

    prof = (await client.get("/api/profile/me", headers=h)).json()
    assert ts_fields("src/features/identity/model.ts", "EmployeeProfile") <= set(prof)
    assert is_iso_date(prof["hiredOn"]) and is_iso_date(prof["leaveBalance"]["asOf"])
    assert {"days", "asOf"} <= set(prof["leaveBalance"]) and isinstance(prof["leaveBalance"]["days"], int)

    page = (await client.get("/api/leave/my", headers=h)).json()
    assert set(page) == {"items", "nextCursor"} and page["nextCursor"] is None
    for item in page["items"]:
        assert ts_fields("src/features/leave/model.ts", "LeaveRequest") <= set(item)
        assert item["type"] == "Leave" and item["status"] in {"Submitted", "Approved", "Rejected", "Cancelled", "Escalated"}
        assert is_iso_date(item["startDate"]) and is_iso_datetime(item["createdAt"])
        for ev in item["history"]:
            assert ts_fields("src/features/leave/model.ts", "LeaveRequestEvent") <= set(ev)
            assert isinstance(ev["actorId"], str) and is_iso_datetime(ev["occurredAt"])

    for n in (await client.get("/api/notifications", headers=h)).json()["items"]:
        assert ts_fields("src/features/notifications/model.ts", "Notification") <= set(n)
        assert is_iso_datetime(n["createdAt"]) and (n["readAt"] is None or is_iso_datetime(n["readAt"]))
        assert n["target"] is None or n["target"]["kind"] in {"request", "course"}

    for c in (await client.get("/api/academy/my", headers=h)).json()["items"]:
        assert ts_fields("src/features/academy/model.ts", "CourseSummary") <= set(c)
        assert ts_fields("src/features/academy/model.ts", "CourseProgress") <= set(c["progress"])
        assert c["progress"]["status"] in {"Assigned", "InProgress", "Completed"}

    ans = (await client.post("/api/ai/ask", headers=h, json={"question": "Сколько дней отпуска положено?"})).json()
    assert ans["kind"] in {"grounded", "no-answer"}
    if ans["kind"] == "grounded":
        assert ans["text"] and ans["sources"]
        for s in ans["sources"]:
            assert ts_fields("src/features/assistant/model.ts", "KnowledgeSource") <= set(s)
    else:
        assert ans["message"] and ans["escalation"] == "HR"


async def test_manager_queues_shape(client, login):
    for who in ("erlan", "aibek"):
        h = await login(who)
        for path in ("/api/leave/pending", "/api/leave/team"):
            for item in (await client.get(path, headers=h)).json()["items"]:
                assert ts_fields("src/features/leave/model.ts", "LeaveRequest") <= set(item)


async def test_money_is_integer(client, login):
    h = await login("aigerim")
    w = (await client.get("/api/ext/wage/summary", headers=h)).json()
    assert all(isinstance(w[k], int) for k in ("earned", "available", "withdrawn", "minAmount"))
    lad = (await client.get("/api/ext/ladder/me", headers=h)).json()
    assert isinstance(lad["raiseToNextMin"], int) and isinstance(lad["current"]["bandMin"], int)
    assert isinstance((await client.get("/api/profile/me", headers=h)).json()["monthlyBase"], int)


