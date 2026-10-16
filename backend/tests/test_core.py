"""Каркас и обязательная часть этапа 1: вход, профиль, отпуск, заявки, уведомления, HR (CLAUDE.md §5, §8)."""

from datetime import timedelta

from app.core import clock


def leave_body(key: str, start_in: int, length: int = 1, comment: str = "") -> dict:
    start = clock.today() + timedelta(days=start_in)
    return {
        "submissionKey": key,
        "startDate": start.isoformat(),
        "endDate": (start + timedelta(days=length - 1)).isoformat(),
        "comment": comment,
    }


async def pending_leave_id(client, headers) -> str:
    r = await client.get("/api/leave/pending", headers=headers)
    assert r.status_code == 200
    return r.json()["items"][0]["id"]


# ---------- вход ----------


async def test_login_and_me(client, login):
    r = await client.get("/api/auth/me", headers=await login("aigerim"))
    assert r.json() == {"id": "emp-aigerim", "displayName": "Айгерим Сейткали", "role": "Employee", "country": "KZ", "lang": "ru"}


async def test_wrong_password_and_no_token(client):
    r = await client.post("/api/auth/login", json={"login": "aigerim", "password": "nope"})
    assert r.status_code == 401 and r.json()["code"] == "INVALID_CREDENTIALS"
    assert r.json()["messageKey"] == "errors.INVALID_CREDENTIALS"
    r = await client.get("/api/profile/me")
    assert r.status_code == 401 and r.json()["kind"] == "unauthenticated"


async def test_demo_login_by_role(client):
    for role, uid in (("Employee", "emp-aigerim"), ("Manager", "emp-erlan"), ("HRAdmin", "emp-daniyar")):
        r = await client.post("/api/demo/login-as", json={"role": role})
        assert r.json()["user"]["id"] == uid
    assert (await client.post("/api/demo/login-as", json={})).status_code == 422


# ---------- профиль ----------


async def test_profile_fields(client, login):
    body = (await client.get("/api/profile/me", headers=await login("aigerim"))).json()
    assert body["company"] == "Jana Post" and body["department"] == "СЦ Алматы · смена Б"
    assert body["manager"]["displayName"] == "Ерлан Мухамедов" and body["hiredOn"] == "2024-06-03"
    # 24 по 1С − 3 дня одобренного отпуска; 7 дней на рассмотрении
    assert body["leaveBalance"] | {"asOf": None} == {"days": 21, "asOf": None, "pendingDays": 7, "availableDays": 14}
    assert body["monthlyBase"] == 240000 and body["gradeCode"] == "SORT-1"
    assert isinstance(body["unreadNotifications"], int)
    assert body["assignedTraining"] == [] or isinstance(body["assignedTraining"], list)


async def test_manager_sees_team_without_salary_but_not_other_team(client, login):
    h = await login("erlan")
    r = await client.get("/api/employees/emp-aigerim", headers=h)
    assert r.status_code == 200 and r.json()["monthlyBase"] is None and r.json()["unreadNotifications"] is None
    assert (await client.get("/api/employees/emp-asel", headers=h)).status_code == 403
    team = (await client.get("/api/team", headers=h)).json()["items"]
    assert {e["id"] for e in team} == {"emp-aigerim", "emp-nurlan"}
    assert all(e["leaveBalance"] is not None for e in team)
    assert (await client.get("/api/team?country=KG", headers=h)).status_code == 403


async def test_hr_team_filters(client, login):
    h = await login("daniyar")
    kg = (await client.get("/api/team?country=KG", headers=h)).json()["items"]
    assert {e["id"] for e in kg} == {"emp-bakyt", "emp-aibek"}
    unit = (await client.get("/api/team?unitId=kz-almaty-sc-a", headers=h)).json()["items"]
    assert {e["id"] for e in unit} == {"emp-gulnara", "emp-asel"}
    assert (await client.get("/api/employees/emp-bakyt", headers=h)).json()["monthlyBase"] == 36000


async def test_employee_cannot_see_others(client, login):
    h = await login("aigerim")
    assert (await client.get("/api/employees/emp-nurlan", headers=h)).status_code == 403
    assert (await client.get("/api/team", headers=h)).status_code == 403
    assert (await client.get("/api/requests/all", headers=h)).status_code == 403
    assert (await client.get("/api/requests/inbox", headers=h)).status_code == 403


async def test_no_endpoints_to_change_official_data(app):
    """Официальные поля только для чтения: кроме языка, профиль не меняется (CLAUDE.md §5.1)."""
    writes = {
        (m, r.path)
        for r in app.routes
        for m in getattr(r, "methods", set())
        if m in {"PUT", "PATCH", "DELETE"} and (r.path.startswith("/api/profile") or r.path.startswith("/api/employees") or r.path.startswith("/api/team"))
    }
    assert writes == set()


# ---------- сквозной сценарий (§5.2 «Готово, когда») ----------


async def test_end_to_end_vacation_flow(client):
    """Вход сотрудника → заявка → вход руководителя → входящие → одобрить → уведомление → карточка с историей и документом."""
    login = lambda name: client.post("/api/auth/login", json={"login": name, "password": "demo1234"})  # noqa: E731
    ha = {"Authorization": f"Bearer {(await login('aigerim')).json()['accessToken']}"}
    r = await client.post("/api/leave", headers=ha, json=leave_body("e2e-1", 40, 3, "тест"))
    assert r.status_code == 201, r.text
    created = r.json()
    assert created["status"] == "Submitted" and created["requestedDays"] == 3 and created["type"] == "Leave"

    he = {"Authorization": f"Bearer {(await login('erlan')).json()['accessToken']}"}
    inbox = (await client.get("/api/requests/inbox", headers=he)).json()["items"]
    assert created["id"] in {i["id"] for i in inbox}
    assert any(n["kind"] == "request.created" for n in (await client.get("/api/notifications", headers=he)).json()["items"])

    r = await client.post(f"/api/requests/{created['id']}/decide", headers=he, json={"decision": "Approved", "expectedVersion": 1})
    assert r.status_code == 200 and r.json()["status"] == "Approved"

    notes = (await client.get("/api/notifications?unreadOnly=true", headers=ha)).json()["items"]
    note = next(n for n in notes if n["target"] == {"kind": "request", "requestId": created["id"]})
    assert note["kind"] == "request.decided" and note["titleKey"] == "notif.request.approved.title" and note["readAt"] is None

    card = (await client.get(f"/api/leave/{created['id']}", headers=ha)).json()
    assert [h["event"] for h in card["history"]] == ["created", "deadline_set", "approved", "document_registered"]
    assert card["history"][-1]["actorId"] == "system"
    assert card["documents"][0]["kind"] == "leave_order" and card["documents"][0]["number"].startswith("DL-")
    assert (await client.get("/api/leave/balance", headers=ha)).json()["days"] == 18  # 21 − 3


async def test_idempotent_submit(client, login):
    ha = await login("aigerim")
    a = await client.post("/api/leave", headers=ha, json=leave_body("same", 50))
    b = await client.post("/api/leave", headers=ha, json=leave_body("same", 50))
    assert a.json()["id"] == b.json()["id"]


async def test_manager_of_other_team_gets_403_by_direct_id(client, login):
    rid = await pending_leave_id(client, await login("erlan"))
    hg = await login("gulnara")
    assert (await client.get(f"/api/requests/{rid}", headers=hg)).status_code == 403
    assert (await client.get(f"/api/leave/{rid}", headers=hg)).status_code == 403
    assert (await client.post(f"/api/requests/{rid}/decide", headers=hg, json={"decision": "Approved"})).status_code == 403


async def test_reject_requires_comment_and_status_unchanged(client, login):
    he = await login("erlan")
    rid = await pending_leave_id(client, he)
    r = await client.post(f"/api/leave/{rid}/decision", headers=he, json={"decision": "Rejected", "expectedVersion": 1, "comment": "  "})
    assert r.status_code == 422 and r.json()["code"] == "COMMENT_REQUIRED"
    assert (await client.get(f"/api/requests/{rid}", headers=he)).json()["status"] == "Submitted"


async def test_cannot_decide_twice_or_with_stale_version(client, login):
    he = await login("erlan")
    rid = await pending_leave_id(client, he)
    r = await client.post(f"/api/requests/{rid}/decide", headers=he, json={"decision": "Approved", "expectedVersion": 9})
    assert r.status_code == 409 and r.json()["code"] == "STALE_VERSION"
    assert (await client.post(f"/api/requests/{rid}/decide", headers=he, json={"decision": "Approved"})).status_code == 200
    r = await client.post(f"/api/requests/{rid}/decide", headers=he, json={"decision": "Rejected", "comment": "передумал"})
    assert r.status_code == 409 and r.json()["code"] == "ALREADY_DECIDED"


async def test_employee_cannot_decide_own_and_can_cancel(client, login):
    ha = await login("aigerim")
    rid = (await client.get("/api/requests/my?status=Submitted", headers=ha)).json()["items"][0]["id"]
    assert (await client.post(f"/api/requests/{rid}/decide", headers=ha, json={"decision": "Approved"})).status_code == 403
    r = await client.post(f"/api/requests/{rid}/cancel", headers=ha)
    assert r.status_code == 200 and r.json()["status"] == "Cancelled"
    assert (await client.post(f"/api/requests/{rid}/cancel", headers=ha)).status_code == 409


async def test_leave_validation_codes(client, login):
    ha = await login("aigerim")
    assert (await client.post("/api/leave", headers=ha, json=leave_body("v1", -1))).json()["code"] == "INVALID_DATES"
    bad = leave_body("v2", 10) | {"endDate": (clock.today() + timedelta(days=5)).isoformat()}
    r = await client.post("/api/leave", headers=ha, json=bad)
    assert r.json()["code"] == "INVALID_DATES" and "endDate" in r.json()["fieldErrors"]
    r = await client.post("/api/leave", headers=ha, json=leave_body("v3", 50, 15))
    assert r.json()["code"] == "INSUFFICIENT_BALANCE" and r.json()["data"]["available"] == 14
    r = await client.post("/api/leave", headers=ha, json=leave_body("v4", 15, 2))  # пересекается с заявкой из seed
    assert r.status_code == 409 and r.json()["code"] == "OVERLAP"


# ---------- реестр HR и «Мои заявки» ----------


async def test_hr_registry_filters(client, login):
    hd = await login("daniyar")
    rows = (await client.get("/api/requests/all", headers=hd)).json()["items"]
    assert {r["type"] for r in rows} == {"vacation", "hr_question"}
    assert {r["status"] for r in rows} >= {"Submitted", "Approved", "Rejected"}
    kg = (await client.get("/api/requests/all?country=KG", headers=hd)).json()["items"]
    assert kg and all(r["employeeId"] == "emp-bakyt" for r in kg)
    unit = (await client.get("/api/requests/all?unitId=kz-almaty-sc-a", headers=hd)).json()["items"]
    assert unit and all(r["employeeId"] == "emp-asel" for r in unit)
    fresh = (await client.post("/api/leave", headers=await login("asel"), json=leave_body("period", 30))).json()["id"]
    today, tomorrow = clock.today(), clock.today() + timedelta(days=1)
    in_period = (await client.get(f"/api/requests/all?from={today}&to={today}", headers=hd)).json()["items"]
    assert fresh in {r["id"] for r in in_period}
    later = (await client.get(f"/api/requests/all?from={tomorrow}", headers=hd)).json()["items"]
    assert later == []
    rid = next(r["id"] for r in rows if r["status"] == "Submitted" and r["type"] == "vacation")
    assert (await client.get(f"/api/requests/{rid}", headers=hd)).status_code == 200
    assert (await client.post(f"/api/requests/{rid}/decide", headers=hd, json={"decision": "Approved"})).status_code == 403


async def test_my_requests_all_types(client, login):
    rows = (await client.get("/api/requests/my", headers=await login("nurlan"))).json()["items"]
    assert {r["typeTitle"] for r in rows} == {"Отпуск", "Вопрос к HR"}


# ---------- вопрос к HR (§5.6) ----------


async def test_hr_question_flow(client, login):
    ha, hd, he = await login("aigerim"), await login("daniyar"), await login("erlan")
    r = await client.post("/api/hr-questions", headers=ha, json={"question": "Положен ли отгул за переработку?", "aiContext": "нет ответа"})
    assert r.status_code == 201 and r.json()["approverKind"] == "hr"
    qid = r.json()["id"]
    assert any(n["target"] and n["target"].get("requestId") == qid for n in (await client.get("/api/notifications", headers=hd)).json()["items"])
    assert qid in {x["id"] for x in (await client.get("/api/requests/inbox", headers=hd)).json()["items"]}
    # Руководитель вопросов к HR не видит
    assert (await client.get(f"/api/requests/{qid}", headers=he)).status_code == 403
    r = await client.post(f"/api/requests/{qid}/decide", headers=hd, json={"decision": "Approved"})
    assert r.json()["code"] == "COMMENT_REQUIRED"
    r = await client.post(f"/api/requests/{qid}/decide", headers=hd, json={"decision": "Approved", "comment": "Да, по ст. 108 — отгул по соглашению сторон."})
    assert r.status_code == 200
    note = (await client.get("/api/notifications?unreadOnly=true", headers=ha)).json()["items"][0]
    assert note["title"] == "HR ответил на ваш вопрос" and "ст. 108" in note["message"]


# ---------- уведомления, язык, демо ----------


async def test_notifications_are_private_and_unread_filter(client, login):
    he = await login("erlan")
    items = (await client.get("/api/notifications", headers=he)).json()["items"]
    unread = (await client.get("/api/notifications?unreadOnly=true", headers=he)).json()["items"]
    assert len(unread) < len(items) and all(n["readAt"] is None for n in unread)
    nid = items[0]["id"]
    assert (await client.post(f"/api/notifications/{nid}/read", headers=await login("aigerim"))).status_code == 404
    r = await client.post(f"/api/notifications/{nid}/read", headers=he)
    assert r.status_code == 200 and r.json()["readAt"] is not None


async def test_kazakh_notifications(client, login):
    ha = await login("aigerim")
    await client.put("/api/auth/me/lang", headers=ha, json={"lang": "kk"})
    he = await login("erlan")
    await client.post(f"/api/requests/{await pending_leave_id(client, he)}/decide", headers=he, json={"decision": "Approved"})
    note = (await client.get("/api/notifications?unreadOnly=true", headers=ha)).json()["items"][0]
    assert note["title"] == "Өтінім мақұлданды" and "Демалыс" in note["message"]


async def test_demo_advance_time_and_reset(client, login):
    assert (await client.post("/api/demo/advance-time", json={"hours": 48})).json()["offsetHours"] == 48
    r = await client.post("/api/demo/reset")
    assert r.status_code == 200 and r.json()["offsetHours"] == 0
    assert (await client.get("/api/profile/me", headers=await login("aigerim"))).status_code == 200
