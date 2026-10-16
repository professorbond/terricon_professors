"""QA А4–А6: крайние случаи бизнес-правил, анонимность по всем путям, демо-режим, базовая безопасность."""

import json
from datetime import timedelta

import jwt
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.core import clock, db
from app.core.config import get_settings
from app.core.org.models import Employee


# ---------- «Зарплата по факту»: смена месяца ----------


async def test_month_change_resets_withdrawal_limit(client, login):
    h = await login("aigerim")
    for _ in range(2):
        assert (await client.post("/api/ext/wage/withdraw", headers=h, json={"amount": 5000})).status_code == 201
    assert (await client.post("/api/ext/wage/withdraw", headers=h, json={"amount": 5000})).json()["code"] == "LIMIT_PER_PERIOD"
    today = clock.today()
    next_month = (today.replace(day=28) + timedelta(days=4)).replace(day=2)
    await client.post("/api/demo/advance-time", json={"hours": (next_month - today).days * 24})
    s = (await client.get("/api/ext/wage/summary", headers=h)).json()
    assert s["period"] == f"{next_month:%Y-%m}" and s["withdrawalsLeft"] == 2 and s["withdrawn"] == 0


# ---------- Гарантии: передача HR по сроку ----------


async def test_escalate_to_hr_after_deadline(client, login):
    hd, he, ha = await login("daniyar"), await login("erlan"), await login("aigerim")
    vac = next(p for p in (await client.get("/api/ext/policies", headers=hd)).json() if p["requestType"] == "vacation")
    await client.put(f"/api/ext/policies/{vac['id']}", headers=hd, json={"onTimeout": "escalate_hr"})
    rid = (await client.get("/api/leave/pending", headers=he)).json()["items"][0]["id"]
    await client.post("/api/demo/advance-time", json={"hours": 47})
    card = (await client.get(f"/api/requests/{rid}", headers=ha)).json()
    assert card["status"] == "Escalated" and card["extensions"]["guarantee"]["resolution"] == "escalated"
    assert rid in {x["id"] for x in (await client.get("/api/requests/inbox", headers=hd)).json()["items"]}
    assert any(n["kind"] == "request.escalated" for n in (await client.get("/api/notifications", headers=ha)).json()["items"])
    assert any(n["kind"] == "request.escalated" for n in (await client.get("/api/notifications", headers=hd)).json()["items"])
    assert (await client.post(f"/api/requests/{rid}/decide", headers=he, json={"decision": "Approved"})).status_code == 403
    assert (await client.post(f"/api/requests/{rid}/decide", headers=hd, json={"decision": "Approved"})).status_code == 200


# ---------- Анонимность обращения по всем путям ----------


ANON_TEXT = "Нарушают технику безопасности в ночную смену"
AUTHOR_MARKERS = ("emp-bakyt", "bakyt", "Бакыт", "Токтогулов")


async def test_anonymous_author_never_leaks(client, login):
    hb, hd, ha = await login("bakyt"), await login("daniyar"), await login("aibek")
    g = (await client.post("/api/ext/grievances", headers=hb, json={"category": "safety", "text": ANON_TEXT, "anonymous": True})).json()
    await client.post("/api/demo/advance-time", json={"hours": 80})  # просрочено → радар, уведомления HR
    paths = [
        f"/api/requests/{g['id']}", "/api/requests/inbox", "/api/requests/inbox?status=all", "/api/requests/all",
        "/api/requests/all?type=grievance", "/api/requests/all?country=KG", "/api/requests/all?unitId=kg-bishkek-wh",
        "/api/notifications", "/api/ext/hr/risks", "/api/ext/hr/risks?country=KG", "/api/ext/hr/xray",
    ]
    for path in paths:
        data = (await client.get(path, headers=hd)).json()
        cards = data.get("items", [data]) if isinstance(data, dict) else data
        for card in cards:
            if isinstance(card, dict) and card.get("id") == g["id"]:
                text = json.dumps(card, ensure_ascii=False)
                assert card["employeeId"] is None and card["employeeName"] is None, path
                assert not any(m in text for m in AUTHOR_MARKERS), path
    # Фильтр, сужающий круг людей (страна KG — 2 человека), не должен показывать анонимное обращение
    kg = (await client.get("/api/requests/all?country=KG", headers=hd)).json()["items"]
    assert g["id"] not in {x["id"] for x in kg}
    # Радар не связывает анонимное обращение с Бакытом
    cards = (await client.get("/api/ext/hr/risks?country=KG", headers=hd)).json()["items"]
    assert not any(s["kind"] == "open_grievance" for c in cards if c["employeeId"] == "emp-bakyt" for s in c["signals"])
    # Уведомления HR про обращение — без автора
    for n in (await client.get("/api/notifications", headers=hd)).json()["items"]:
        if n["target"] and n["target"].get("requestId") == g["id"]:
            assert not any(m in n["title"] + n["message"] + json.dumps(n["params"], ensure_ascii=False) for m in AUTHOR_MARKERS)
    # Руководитель автора: 403 и текст ошибки без имени
    r = await client.get(f"/api/requests/{g['id']}", headers=ha)
    assert r.status_code == 403 and not any(m in r.text for m in AUTHOR_MARKERS)
    # Рентген: обращение не попадает в метрики руководителя
    xr = (await client.get("/api/ext/hr/xray?country=KG", headers=hd)).json()["items"][0]
    # Отпуск Бакыта за 80 ч одобрен системой (KG: 72 ч), обращение адресовано HR и в метрики руководителя не входит
    assert xr["pendingNow"] == 0 and xr["lateDecisions"] == 1


# ---------- Academy: правильные ответы не уходят клиенту ----------


async def test_correct_answers_never_sent(client, login):
    ha, he, hd = await login("aigerim"), await login("erlan"), await login("daniyar")
    responses = [
        await client.get("/api/academy/courses", headers=ha),
        await client.get("/api/academy/my", headers=ha),
        await client.get("/api/academy/courses/course-safety", headers=ha),
        await client.get("/api/academy/courses/course-returns", headers=ha),
        await client.get("/api/academy/courses/course-safety/progress", headers=ha),
        await client.post("/api/academy/lessons/l-saf-2/complete", headers=ha),
        await client.post("/api/academy/courses/course-safety/submit", headers=ha, json={"answers": [0, 0, 0, 0]}),
        await client.get("/api/academy/progress", headers=he),
        await client.get("/api/academy/progress", headers=hd),
        await client.get("/api/profile/me", headers=ha),
        await client.get("/api/ext/ladder/course-tags", headers=ha),
    ]
    for r in responses:
        assert r.status_code in (200, 201)
        body = r.text
        assert "correctIndex" not in body and "correct_index" not in body
    # Ответ на неверную сдачу не раскрывает, какие варианты верные — только количество
    sub = responses[6].json()
    assert set(sub) == {"score", "passed", "passingScore", "correct", "total", "progress"} and isinstance(sub["correct"], int)


# ---------- i18n: у каждого ключа есть ru и kk ----------


def test_every_ru_key_has_kk(app):
    from app.core import i18n

    missing = sorted(set(i18n._catalog["ru"]) - set(i18n._catalog["kk"]))
    assert missing == [], missing


# ---------- Демо-режим ----------


async def test_demo_endpoints_absent_when_demo_off():
    from app.core.config import Settings
    from app.main import create_app

    app = create_app(Settings(demo_mode=False, auto_migrate=False, auto_seed=False, tick_interval_seconds=0))
    paths = set(app.openapi()["paths"])
    assert not any(p.startswith("/api/demo") for p in paths) and "/api/auth/login" in paths
    create_app()  # вернуть реестры


async def test_reset_is_repeatable(client, login):
    for _ in range(3):
        assert (await client.post("/api/demo/reset")).status_code == 200
    assert len((await client.get("/api/requests/all", headers=await login("daniyar"))).json()["items"]) == 8


# ---------- Безопасность ----------


async def test_passwords_hashed_and_jwt_expires(client):
    async with db.sessionmaker()() as s:
        emps = list(await s.scalars(select(Employee)))
    assert all(e.password_hash.startswith("pbkdf2$") and "demo1234" not in e.password_hash for e in emps)
    token = (await client.post("/api/auth/login", json={"login": "aigerim", "password": "demo1234"})).json()["accessToken"]
    payload = jwt.decode(token, get_settings().jwt_secret, algorithms=["HS256"])
    assert 0 < payload["exp"] - payload.get("iat", payload["exp"] - 12 * 3600) <= 12 * 3600 + 5
    expired = jwt.encode({"sub": "emp-aigerim", "exp": 1}, get_settings().jwt_secret, algorithm="HS256")
    assert (await client.get("/api/auth/me", headers={"Authorization": f"Bearer {expired}"})).status_code == 401
    alg_none = jwt.encode({"sub": "emp-daniyar"}, key="", algorithm="none")
    assert (await client.get("/api/requests/all", headers={"Authorization": f"Bearer {alg_none}"})).status_code == 401


async def test_unexpected_error_has_no_stacktrace(app):
    @app.get("/api/_qa_boom")
    async def boom():
        raise RuntimeError("секретная деталь внутренней ошибки")

    async with AsyncClient(transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://t") as c:
        r = await c.get("/api/_qa_boom")
    assert r.status_code == 500 and "Traceback" not in r.text and "секретная" not in r.text


SQLISH = ["' OR 1=1--", "\"; DROP TABLE employees; --", "%", "_", "\\", "<script>alert(1)</script>", "ё😀", "a" * 300]


@pytest.mark.parametrize("value", SQLISH)
async def test_filters_survive_sqlish_input(client, login, value):
    hd = await login("daniyar")
    for path, params in [
        ("/api/requests/all", {"type": value}), ("/api/requests/all", {"status": value}), ("/api/requests/all", {"unitId": value}),
        ("/api/requests/all", {"country": value}), ("/api/team", {"unitId": value}), ("/api/requests/my", {"type": value}),
        ("/api/ext/hr/risks", {"country": value}), ("/api/ext/kb/gaps", {"country": value}), ("/api/academy/progress", {"unitId": value}),
    ]:
        r = await client.get(path, headers=hd, params=params)
        assert r.status_code in (200, 422), (path, value, r.status_code)
        if r.status_code == 200:
            assert r.json()["items"] == [] if isinstance(r.json(), dict) else r.json() == []
    for path in (f"/api/employees/{value}", f"/api/requests/{value}", f"/api/leave/{value}"):
        assert (await client.get(path, headers=hd)).status_code in (403, 404, 422)
    r = await client.post("/api/ai/ask", headers=hd, json={"question": value})
    assert r.status_code in (200, 422)
    # Сохранилось ли всё на месте
    assert len((await client.get("/api/requests/all", headers=hd)).json()["items"]) == 8
