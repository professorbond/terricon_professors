"""Точки расширения каркаса: события движка и флаги фич."""

from app.core.config import Settings
from app.core.errors import validation
from app.core.events import events


async def test_before_decision_handler_can_veto_any_request_type(client, login):
    """Так модуль гарантий запрещает отказ без кода причины — не трогая модуль «Отпуск»."""

    async def require_reason(request, decision, reason_code, **_):
        if decision == "Rejected" and not reason_code:
            raise validation("REASON_REQUIRED", "Выберите причину из справочника", "reasonCode")

    events.subscribe("request.before_decision", require_reason)
    he = await login("erlan")
    rid = (await client.get("/api/leave/requests/pending", headers=he)).json()["items"][0]["id"]
    r = await client.post(f"/api/requests/{rid}/decide", headers=he, json={"decision": "Rejected", "comment": "нет людей в смене"})
    assert r.status_code == 422 and r.json()["code"] == "REASON_REQUIRED"
    assert (await client.get(f"/api/requests/{rid}", headers=he)).json()["status"] == "Submitted"
    r = await client.post(
        f"/api/requests/{rid}/decide", headers=he, json={"decision": "Rejected", "comment": "нет людей в смене", "reasonCode": "STAFFING"}
    )
    assert r.status_code == 200 and r.json()["decisionReasonCode"] == "STAFFING"


def test_feature_flags():
    assert Settings(ext_features="*").feature_enabled("wage_access")
    assert Settings(ext_features="guarantees, wage_access").feature_enabled("wage_access")
    assert not Settings(ext_features="guarantees").feature_enabled("wage_access")
    assert not Settings(ext_features="").feature_enabled("wage_access")
    assert Settings(ext_features="").feature_enabled(None)  # модули без флага всегда включены


async def test_settings_endpoint(client, login):
    r = await client.get("/api/settings", headers=await login("bakyt"))
    assert r.json()["country"] == "KG" and r.json()["demoMode"] is True
