"""Каркас: вход, роли, движок заявок, права (CLAUDE.md §4.3, §8)."""

from datetime import timedelta

from app.core import clock


async def pending_leave_id(client, headers) -> str:
    r = await client.get("/api/leave/requests/pending", headers=headers)
    assert r.status_code == 200
    return r.json()["items"][0]["id"]


async def test_login_and_me(client, login):
    h = await login("aigerim")
    r = await client.get("/api/auth/me", headers=h)
    assert r.json() == {"id": "emp-aigerim", "displayName": "Айгерим Сейткали", "role": "Employee", "country": "KZ", "lang": "ru"}


async def test_wrong_password_and_no_token(client):
    r = await client.post("/api/auth/login", json={"login": "aigerim", "password": "nope"})
    assert r.status_code == 401 and r.json()["code"] == "INVALID_CREDENTIALS"
    r = await client.get("/api/profile/me")
    assert r.status_code == 401 and r.json()["kind"] == "unauthenticated"


async def test_profile_is_read_only_data_from_zup(client, login):
    r = await client.get("/api/profile/me", headers=await login("aigerim"))
    body = r.json()
    assert body["manager"]["displayName"] == "Ерлан Мухамедов"
    assert body["leaveBalance"]["days"] == 24
    assert body["monthlyBase"] == 240000


async def test_manager_sees_team_without_salary_but_not_other_team(client, login):
    h = await login("erlan")
    r = await client.get("/api/employees/emp-aigerim", headers=h)
    assert r.status_code == 200 and r.json()["monthlyBase"] is None
    assert (await client.get("/api/employees/emp-asel", headers=h)).status_code == 403
    team = await client.get("/api/team", headers=h)
    assert {e["id"] for e in team.json()["items"]} == {"emp-aigerim", "emp-nurlan"}


async def test_employee_cannot_see_others(client, login):
    h = await login("aigerim")
    assert (await client.get("/api/employees/emp-nurlan", headers=h)).status_code == 403
    assert (await client.get("/api/team", headers=h)).status_code == 403
    assert (await client.get("/api/requests", headers=h)).status_code == 403
    assert (await client.get("/api/requests/inbox", headers=h)).status_code == 403


async def test_full_request_flow(client, login):
    """Создать → inbox руководителя → решение → уведомление автору → история."""
    ha, he = await login("aigerim"), await login("erlan")
    start = clock.today() + timedelta(days=40)
    r = await client.post(
        "/api/leave/requests",
        headers=ha,
        json={"submissionKey": "t-1", "startDate": start.isoformat(), "endDate": (start + timedelta(days=2)).isoformat(), "comment": "тест"},
    )
    assert r.status_code == 201, r.text
    created = r.json()
    assert created["status"] == "Submitted" and created["requestedDays"] == 3

    # Повторная отправка с тем же ключом не создаёт дубль
    again = await client.post(
        "/api/leave/requests",
        headers=ha,
        json={"submissionKey": "t-1", "startDate": start.isoformat(), "endDate": (start + timedelta(days=2)).isoformat()},
    )
    assert again.json()["id"] == created["id"]

    inbox = await client.get("/api/requests/inbox", headers=he)
    assert created["id"] in {i["id"] for i in inbox.json()["items"]}

    r = await client.post(
        f"/api/leave/requests/{created['id']}/decision", headers=he, json={"decision": "Approved", "expectedVersion": 1}
    )
    assert r.status_code == 200 and r.json()["status"] == "Approved"
    events = [h["event"] for h in r.json()["history"]]
    assert events == ["created", "approved", "document_registered"]

    notes = (await client.get("/api/notifications?unreadOnly=true", headers=ha)).json()["items"]
    assert any(n["target"] == {"kind": "request", "requestId": created["id"]} for n in notes)

    # Приказ ушёл в 1С через Documentolog — остаток уменьшился
    assert (await client.get("/api/leave/balance", headers=ha)).json()["days"] == 21


async def test_manager_of_other_team_gets_403_by_direct_id(client, login):
    rid = await pending_leave_id(client, await login("erlan"))
    hg = await login("gulnara")
    assert (await client.get(f"/api/requests/{rid}", headers=hg)).status_code == 403
    r = await client.post(f"/api/requests/{rid}/decide", headers=hg, json={"decision": "Approved"})
    assert r.status_code == 403


async def test_reject_requires_comment_and_status_unchanged(client, login):
    he = await login("erlan")
    rid = await pending_leave_id(client, he)
    r = await client.post(f"/api/requests/{rid}/decide", headers=he, json={"decision": "Rejected", "comment": "  "})
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
    rid = (await client.get("/api/requests/my", headers=ha)).json()["items"][0]["id"]
    assert (await client.post(f"/api/requests/{rid}/decide", headers=ha, json={"decision": "Approved"})).status_code == 403
    r = await client.post(f"/api/requests/{rid}/cancel", headers=ha)
    assert r.status_code == 200 and r.json()["status"] == "Cancelled"


async def test_hr_sees_registry_but_cannot_decide_manager_requests(client, login):
    hd = await login("daniyar")
    rows = (await client.get("/api/requests", headers=hd)).json()["items"]
    assert len(rows) == 4
    rid = next(r["id"] for r in rows if r["status"] == "Submitted")
    assert (await client.get(f"/api/requests/{rid}", headers=hd)).status_code == 200
    assert (await client.post(f"/api/requests/{rid}/decide", headers=hd, json={"decision": "Approved"})).status_code == 403


async def test_leave_validation(client, login):
    ha = await login("aigerim")
    past = clock.today() - timedelta(days=1)
    r = await client.post("/api/leave/requests", headers=ha, json={"submissionKey": "v1", "startDate": past.isoformat(), "endDate": past.isoformat()})
    assert r.json()["code"] == "START_IN_PAST"
    start = clock.today() + timedelta(days=50)
    r = await client.post(
        "/api/leave/requests", headers=ha, json={"submissionKey": "v2", "startDate": start.isoformat(), "endDate": (start + timedelta(days=30)).isoformat()}
    )
    assert r.json()["code"] == "INSUFFICIENT_BALANCE" and r.json()["data"]["available"] == 24


async def test_notifications_are_private(client, login):
    he = await login("erlan")
    nid = (await client.get("/api/notifications", headers=he)).json()["items"][0]["id"]
    assert (await client.post(f"/api/notifications/{nid}/read", headers=await login("aigerim"))).status_code == 404
    r = await client.post(f"/api/notifications/{nid}/read", headers=he)
    assert r.status_code == 200 and r.json()["readAt"] is not None


async def test_demo_advance_time_and_reset(client, login):
    r = await client.post("/api/demo/advance-time", json={"hours": 48})
    assert r.json()["offsetHours"] == 48
    r = await client.post("/api/demo/reset")
    assert r.status_code == 200 and r.json()["offsetHours"] == 0
    assert (await client.get("/api/demo/personas")).status_code == 200
    assert (await client.get("/api/profile/me", headers=await login("aigerim"))).status_code == 200


async def test_kazakh_notifications(client, login):
    ha = await login("aigerim")
    await client.put("/api/auth/me/lang", headers=ha, json={"lang": "kk"})
    he = await login("erlan")
    rid = await pending_leave_id(client, he)
    await client.post(f"/api/requests/{rid}/decide", headers=he, json={"decision": "Approved"})
    note = (await client.get("/api/notifications?unreadOnly=true", headers=ha)).json()["items"][0]
    assert note["title"] == "Өтінім мақұлданды" and "Демалыс" in note["message"]
