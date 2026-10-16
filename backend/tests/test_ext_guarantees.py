"""Гарантии и политики (CLAUDE.md §7.1)."""

from datetime import timedelta

from app.core import clock
from app.core.config import get_settings


async def aigerim_pending(client, he):
    return (await client.get("/api/leave/pending", headers=he)).json()["items"][0]


async def test_deadline_set_on_created_and_visible_in_card(client, login):
    ha = await login("aigerim")
    start = clock.today() + timedelta(days=60)
    r = await client.post("/api/leave", headers=ha, json={"submissionKey": "g1", "startDate": str(start), "endDate": str(start)})
    card = r.json()
    g = card["extensions"]["guarantee"]
    assert g["resolution"] == "none" and g["overdue"] is False
    created = card["createdAt"].replace("Z", "+00:00")
    from datetime import datetime
    assert datetime.fromisoformat(g["deadlineAt"]) - datetime.fromisoformat(created) == timedelta(hours=48)
    assert "deadline_set" in [h["event"] for h in card["history"]]
    note = (await client.get("/api/notifications?unreadOnly=true", headers=ha)).json()["items"][0]
    assert note["kind"] == "guarantee.deadline" and "ответ до" in note["message"]


async def test_kg_has_different_sla(client, login):
    hb = await login("bakyt")
    start = clock.today() + timedelta(days=60)
    card = (await client.post("/api/leave", headers=hb, json={"submissionKey": "g2", "startDate": str(start), "endDate": str(start)})).json()
    from datetime import datetime
    delta = datetime.fromisoformat(card["extensions"]["guarantee"]["deadlineAt"]) - datetime.fromisoformat(card["createdAt"].replace("Z", "+00:00"))
    assert delta == timedelta(hours=72)


async def test_reject_without_reason_or_unknown_reason_fails_status_unchanged(client, login):
    he = await login("erlan")
    rid = (await aigerim_pending(client, he))["id"]
    for body, code in (
        ({"decision": "Rejected", "comment": "В смене никого не остаётся"}, "REASON_REQUIRED"),
        ({"decision": "Rejected", "comment": "В смене никого не остаётся", "reasonCode": "BECAUSE"}, "UNKNOWN_REASON"),
        ({"decision": "Rejected", "comment": "нет", "reasonCode": "STAFFING"}, "COMMENT_REQUIRED"),
        ({"decision": "Rejected", "comment": "Отказ", "reasonCode": "NOT_HR_TOPIC"}, "UNKNOWN_REASON"),  # не для отпуска
    ):
        r = await client.post(f"/api/requests/{rid}/decide", headers=he, json=body)
        assert r.status_code == 422 and r.json()["code"] == code, (body, r.json())
    assert (await client.get(f"/api/requests/{rid}", headers=he)).json()["status"] == "Submitted"
    r = await client.post(f"/api/requests/{rid}/decide", headers=he, json={"decision": "Rejected", "comment": "В смене никого не остаётся", "reasonCode": "STAFFING"})
    assert r.status_code == 200 and r.json()["decisionReasonCode"] == "STAFFING"


async def test_soft_mode_without_reason_code(client, login, monkeypatch):
    monkeypatch.setattr(get_settings(), "guarantees_require_reason", False)
    he = await login("erlan")
    rid = (await aigerim_pending(client, he))["id"]
    r = await client.post(f"/api/requests/{rid}/decide", headers=he, json={"decision": "Rejected", "comment": "В смене никого не остаётся"})
    assert r.status_code == 200 and r.json()["decisionReasonCode"] == "OTHER"


async def test_auto_approve_after_deadline(client, login):
    he, ha = await login("erlan"), await login("aigerim")
    rid = (await aigerim_pending(client, he))["id"]
    await client.post("/api/demo/advance-time", json={"hours": 45})  # 47 ч от создания
    assert (await client.get(f"/api/requests/{rid}", headers=ha)).json()["status"] == "Submitted"
    await client.post("/api/demo/advance-time", json={"hours": 2})  # sla+1ч от создания (создана 2 ч назад)
    card = (await client.get(f"/api/leave/{rid}", headers=ha)).json()
    assert card["status"] == "Approved" and card["decidedBySystem"] is True
    assert card["extensions"]["guarantee"]["resolution"] == "auto_approved"
    assert [h["actorId"] for h in card["history"] if h["event"] == "approved"] == ["system"]
    note = (await client.get("/api/notifications?unreadOnly=true", headers=ha)).json()["items"][0]
    assert "по политике HR" in note["message"]
    assert card["documents"]  # приказ сформирован и при автоодобрении


async def test_hr_question_overdue_marked(client, login):
    hd = await login("daniyar")
    rows = (await client.get("/api/requests/all?type=hr_question", headers=hd)).json()["items"]
    await client.post("/api/demo/advance-time", json={"hours": 1})  # тик
    q = (await client.get(f"/api/requests/{rows[0]['id']}", headers=hd)).json()
    assert q["extensions"]["guarantee"]["resolution"] == "overdue" and q["extensions"]["guarantee"]["overdue"] is True
    assert any(n["kind"] == "guarantee.overdue" for n in (await client.get("/api/notifications", headers=hd)).json()["items"])


async def test_auto_approve_forbidden_for_money(client, login):
    hd = await login("daniyar")
    policies = (await client.get("/api/ext/policies", headers=hd)).json()
    wage = next(p for p in policies if p["requestType"] == "wage_access")
    r = await client.put(f"/api/ext/policies/{wage['id']}", headers=hd, json={"onTimeout": "auto_approve", "slaHours": 24})
    assert r.status_code == 422 and r.json()["code"] == "AUTO_APPROVE_FORBIDDEN"
    again = (await client.get("/api/ext/policies", headers=hd)).json()
    assert next(p for p in again if p["requestType"] == "wage_access")["onTimeout"] is None


async def test_policies_access(client, login):
    ha, hd = await login("aigerim"), await login("daniyar")
    assert {p["requestType"] for p in (await client.get("/api/ext/policies", headers=ha)).json()} >= {"vacation", "wage_access"}
    assert (await client.get("/api/ext/policies?country=KG", headers=ha)).status_code == 403
    vac = next(p for p in (await client.get("/api/ext/policies?country=KG", headers=hd)).json() if p["requestType"] == "vacation")
    assert vac["slaHours"] == 72
    assert (await client.put(f"/api/ext/policies/{vac['id']}", headers=ha, json={"slaHours": 1})).status_code == 403
    r = await client.put(f"/api/ext/policies/{vac['id']}", headers=hd, json={"slaHours": 24})
    assert r.status_code == 200 and r.json()["slaHours"] == 24


async def test_reasons_and_summary(client, login):
    ha = await login("aigerim")
    codes = {r["code"] for r in (await client.get("/api/ext/guarantees/reasons?type=vacation", headers=ha)).json()}
    assert codes == {"STAFFING", "PEAK_LOAD", "TEAM_OVERLAP", "LATE_NOTICE", "OTHER"}
    s = (await client.get("/api/ext/guarantees/summary/me", headers=ha)).json()
    assert len(s["openRequests"]) == 1 and s["rejectionsWithoutReason"] == 0
    assert s["nextSalaryReview"] < str(clock.today())  # пересмотр просрочен: 14 мес назад + 12


async def test_works_on_vacation_without_leave_module_changes():
    """Гарантии подключены событиями: модуль отпуска их не импортирует."""
    import pathlib

    src = "".join(p.read_text() for p in pathlib.Path("app/modules/leave").glob("*.py"))
    assert "ext_guarantees" not in src
